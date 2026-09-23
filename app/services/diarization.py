"""Speaker diarization interface with an optional local pyannote adapter."""
from app.config import DEMO_MODE, PYANNOTE_PIPELINE
from app.services.transcription import DiarizationResult, DiarizationTurn


class Diarizer:
    def diarize(self, audio_path: str) -> DiarizationResult:
        raise NotImplementedError


class DemoDiarizer(Diarizer):
    def diarize(self, audio_path: str) -> DiarizationResult:
        return DiarizationResult([])  # Demo transcript includes its speaker assignments.


class PyannoteDiarizer(Diarizer):
    def __init__(self, pipeline_name=PYANNOTE_PIPELINE):
        from pyannote.audio import Pipeline
        self.pipeline = Pipeline.from_pretrained(pipeline_name)

    def diarize(self, audio_path: str) -> DiarizationResult:
        annotation = self.pipeline(audio_path)
        return DiarizationResult([DiarizationTurn(turn.start, turn.end, speaker)
                                  for turn, _, speaker in annotation.itertracks(yield_label=True)])


def get_diarizer():
    return DemoDiarizer() if DEMO_MODE else PyannoteDiarizer()
