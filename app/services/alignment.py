"""Align local ASR segments to diarization turns by maximum time overlap."""
from app.services.transcription import AlignedTranscript, TranscriptSegment


def align_segments(segments, turns):
    # Accept both the original list-of-dicts interface and the new domain result.
    if hasattr(segments, "segments"):
        segments = segments.segments
    if hasattr(turns, "turns"):
        turns = turns.turns
    aligned = []
    for segment in segments:
        best = None
        overlap = 0
        for turn in turns:
            turn_start = turn["start"] if isinstance(turn, dict) else turn.start
            turn_end = turn["end"] if isinstance(turn, dict) else turn.end
            turn_speaker = turn["speaker"] if isinstance(turn, dict) else turn.speaker
            amount = max(0, min(segment.end, turn_end) - max(segment.start, turn_start))
            if amount > overlap:
                overlap, best = amount, turn_speaker
        aligned.append({"start": segment.start, "end": segment.end, "text": segment.text,
                        "language": segment.language, "speaker": best or "SPEAKER_00"})
    return aligned


def align_transcription(transcription, diarization) -> AlignedTranscript:
    """Domain-oriented wrapper for combining independent ASR and diarization results."""
    aligned = align_segments(transcription, diarization)
    return AlignedTranscript([TranscriptSegment(item["start"], item["end"], item["text"],
                                                item["language"], item["speaker"])
                              for item in aligned])
