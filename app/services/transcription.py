"""Local speech-to-text adapters and transcript domain structures."""
from dataclasses import dataclass
from typing import Optional

from app.config import DEMO_MODE, WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    language: str = ""
    speaker: str = "SPEAKER_00"


@dataclass
class TranscriptionResult:
    segments: list[TranscriptSegment]
    language: Optional[str] = None


@dataclass
class DiarizationTurn:
    start: float
    end: float
    speaker: str


@dataclass
class DiarizationResult:
    turns: list[DiarizationTurn]


@dataclass
class AlignedTranscript:
    segments: list[TranscriptSegment]


class TranscriptionError(RuntimeError):
    """A safe, user-displayable transcription failure."""


class Transcriber:
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        raise NotImplementedError


class DemoTranscriber(Transcriber):
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        return TranscriptionResult([TranscriptSegment(0, 8, "Демонстрационная транскрипция встречи", "ru")], "ru")


class FasterWhisperTranscriber(Transcriber):
    def __init__(self, model_name=WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscriptionError("faster-whisper is not installed. Install it with: pip install faster-whisper") from exc
        try:
            self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
        except Exception as exc:
            raise TranscriptionError(f"Could not load local Whisper model '{model_name}'. Check the model name and local cache/network access.") from exc

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        try:
            segments, info = self.model.transcribe(audio_path, language=None, vad_filter=True)
            # Iteration performs decoding and may itself fail for unreadable media.
            result = [TranscriptSegment(float(s.start), float(s.end), s.text.strip(),
                                        getattr(s, "language", None) or getattr(info, "language", None) or "",
                                        "SPEAKER_00") for s in segments if s.text.strip()]
            return TranscriptionResult(result, getattr(info, "language", None))
        except Exception as exc:
            raise TranscriptionError("Audio could not be read or transcribed. Check that the recording is valid and try again.") from exc


def get_transcriber():
    return DemoTranscriber() if DEMO_MODE else FasterWhisperTranscriber()
