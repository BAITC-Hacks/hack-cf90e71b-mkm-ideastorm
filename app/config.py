"""Application settings loaded from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_MODE = os.getenv("DEMO_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "qazmeeting.db")))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", os.getenv("LOCAL_MODEL_DEVICE", "cpu"))
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads")))
PYANNOTE_PIPELINE = os.getenv("PYANNOTE_PIPELINE", "pyannote/speaker-diarization-3.1")
