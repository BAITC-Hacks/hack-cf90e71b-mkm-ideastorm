"""FastAPI application for the QazMeeting AI local-first demo."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import BASE_DIR, DEMO_MODE
from app.database import connection, init_db, one, rows, seed_demo
from app.services.exports import to_docx, to_pdf
from app.services.speakers import rename_speaker

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
