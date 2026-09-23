"""Speech-to-text interface; the production adapter runs faster-whisper locally."""
from dataclasses import dataclass

from app.config import DEMO_MODE, WHISPER_MODEL


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    language: str = ""


class Transcriber:
    def transcribe(self, audio_path: str) -> list[TranscriptSegment]:
        raise NotImplementedError


class DemoTranscriber(Transcriber):
    def transcribe(self, audio_path: str) -> list[TranscriptSegment]:
        return [TranscriptSegment(0, 8, "Демонстрационная транскрипция встречи", "ru")]


class FasterWhisperTranscriber(Transcriber):
    def __init__(self, model_name=WHISPER_MODEL):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: str) -> list[TranscriptSegment]:
        segments, _ = self.model.transcribe(audio_path, language=None, vad_filter=True)
        return [TranscriptSegment(s.start, s.end, s.text.strip(), "") for s in segments]


def get_transcriber():
    return DemoTranscriber() if DEMO_MODE else FasterWhisperTranscriber()
