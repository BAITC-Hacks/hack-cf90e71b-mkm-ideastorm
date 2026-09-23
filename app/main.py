"""FastAPI application for the QazMeeting AI local-first demo."""
from pathlib import Path
from datetime import date, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from typing import Optional
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import BASE_DIR, DEMO_MODE, UPLOAD_DIR
from app.database import connection, init_db, one, rows, seed_demo
from app.services.exports import to_docx, to_pdf
from app.services.speakers import rename_speaker
from app.services.transcription import get_transcriber, TranscriptionError

SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".mp4"}
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024

app = FastAPI(title="QazMeeting AI", description="Локальная обработка встреч")


@app.on_event("startup")
def startup():
    init_db()
    if DEMO_MODE:
        seed_demo()


class MeetingCreate(BaseModel):
    title: str
    meeting_date: str


class StatusUpdate(BaseModel):
    status: str


class SpeakerRename(BaseModel):
    display_name: str


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": DEMO_MODE, "processing": "local"}


@app.get("/api/dashboard")
def dashboard():
    meetings = rows("SELECT * FROM meetings ORDER BY meeting_date DESC, id DESC")
    actions = rows("SELECT status, deadline FROM action_items")
    return {"meetings": meetings, "meeting_count": len(meetings), "action_count": len(actions),
            "overdue_count": sum(1 for x in actions if x["status"] == "Overdue"),
            "completed_count": sum(1 for x in actions if x["status"] == "Completed"), "demo_mode": DEMO_MODE}


@app.post("/api/meetings", status_code=201)
def create_meeting(payload: MeetingCreate):
    with connection() as db:
        cursor = db.execute("INSERT INTO meetings(title,meeting_date,created_at) VALUES(?,?,datetime('now'))", (payload.title, payload.meeting_date))
        meeting_id = cursor.lastrowid
    return {"id": meeting_id, "title": payload.title, "meeting_date": payload.meeting_date}


@app.post("/api/meetings/upload", status_code=201)
async def upload_meeting(title: str = Form(...), recording: Optional[UploadFile] = File(None)):
    if DEMO_MODE:
        raise HTTPException(403, "Audio upload is available in local-AI mode. Set DEMO_MODE=false.")
    title = title.strip()
    if not title:
        raise HTTPException(400, "Enter a meeting title.")
    if not recording or not recording.filename:
        raise HTTPException(400, "Choose a recording to upload.")
    suffix = Path(recording.filename).suffix.lower()
    if suffix not in SUPPORTED_AUDIO:
        raise HTTPException(415, "Unsupported file type. Choose an MP3, WAV, M4A, or MP4 recording.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    size = 0
    try:
        with audio_path.open("wb") as target:
            while chunk := await recording.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Recording is too large. Maximum upload size is 1 GB.")
                target.write(chunk)
        if size == 0:
            raise HTTPException(400, "The selected recording is empty.")
        with connection() as db:
            meeting_id = db.execute(
                "INSERT INTO meetings(title,meeting_date,created_at,processing_status) VALUES(?,?,?,?)",
                (title, date.today().isoformat(), datetime.now().isoformat(timespec="seconds"), "processing")
            ).lastrowid
        try:
            result = get_transcriber().transcribe(str(audio_path))
        except TranscriptionError as exc:
            with connection() as db:
                db.execute("UPDATE meetings SET processing_status='failed', processing_error=? WHERE id=?", (str(exc), meeting_id))
            raise HTTPException(503, str(exc)) from exc
        except Exception as exc:
            with connection() as db:
                db.execute("UPDATE meetings SET processing_status='failed', processing_error=? WHERE id=?",
                           ("Transcription failed. Check the local model and recording, then try again.", meeting_id))
            raise HTTPException(500, "Transcription failed. Check the local model and recording, then try again.") from exc
        with connection() as db:
            db.execute("INSERT INTO speakers(meeting_id,speaker_key,display_name) VALUES(?,?,?)",
                       (meeting_id, "SPEAKER_00", "Speaker 1 (unverified)"))
            db.executemany("INSERT INTO segments(meeting_id,speaker_key,start_seconds,end_seconds,text,language) VALUES(?,?,?,?,?,?)",
                           [(meeting_id, segment.speaker, segment.start, segment.end, segment.text, segment.language)
                            for segment in result.segments])
            db.execute("UPDATE meetings SET processing_status='complete' WHERE id=?", (meeting_id,))
        return {"id": meeting_id, "title": title, "processing_status": "complete"}
    except HTTPException:
        audio_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(500, "Could not save the recording locally. Check available disk space and permissions.") from exc
    finally:
        await recording.close()


@app.get("/api/meetings/{meeting_id}")
def meeting_detail(meeting_id: int):
    meeting = one("SELECT * FROM meetings WHERE id=?", (meeting_id,))
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    speakers = {s["speaker_key"]: s["display_name"] for s in rows("SELECT * FROM speakers WHERE meeting_id=?", (meeting_id,))}
    segments = rows("SELECT * FROM segments WHERE meeting_id=? ORDER BY start_seconds", (meeting_id,))
    for segment in segments:
        segment["display_name"] = speakers.get(segment["speaker_key"], segment["speaker_key"])
    actions = rows("SELECT * FROM action_items WHERE meeting_id=? ORDER BY deadline", (meeting_id,))
    return {"meeting": meeting, "speakers": [{"speaker_key": k, "display_name": v} for k, v in speakers.items()],
            "segments": segments, "action_items": actions}


@app.patch("/api/action-items/{item_id}")
def update_action(item_id: int, payload: StatusUpdate):
    if payload.status not in {"In progress", "Completed", "Overdue"}:
        raise HTTPException(400, "Unsupported status")
    with connection() as db:
        result = db.execute("UPDATE action_items SET status=? WHERE id=?", (payload.status, item_id))
    if not result.rowcount:
        raise HTTPException(404, "Action item not found")
    return {"id": item_id, "status": payload.status}


@app.patch("/api/meetings/{meeting_id}/speakers/{speaker_key}")
def update_speaker(meeting_id: int, speaker_key: str, payload: SpeakerRename):
    if not payload.display_name.strip():
        raise HTTPException(400, "Display name cannot be empty")
    if not rename_speaker(meeting_id, speaker_key, payload.display_name):
        raise HTTPException(404, "Speaker not found")
    return {"speaker_key": speaker_key, "display_name": payload.display_name.strip()}


@app.get("/api/meetings/{meeting_id}/export/{kind}")
def export_meeting(meeting_id: int, kind: str):
    data = meeting_detail(meeting_id)
    if kind == "docx":
        content, media, suffix = to_docx(data["meeting"], data["segments"], data["action_items"]), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
    elif kind == "pdf":
        content, media, suffix = to_pdf(data["meeting"], data["segments"], data["action_items"]), "application/pdf", "pdf"
    else:
        raise HTTPException(404, "Unsupported export format")
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="qazmeeting-{meeting_id}.{suffix}"'})


app.mount("/", StaticFiles(directory=BASE_DIR / "app" / "static", html=True), name="static")
