"""Speaker display-name operations."""
from app.database import connection


def rename_speaker(meeting_id: int, speaker_key: str, name: str):
    with connection() as db:
        result = db.execute("UPDATE speakers SET display_name=? WHERE meeting_id=? AND speaker_key=?", (name.strip(), meeting_id, speaker_key))
        return result.rowcount > 0
