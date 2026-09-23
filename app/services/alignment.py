"""Align local ASR segments to diarization turns by maximum time overlap."""


def align_segments(segments, turns):
    aligned = []
    for segment in segments:
        best = None
        overlap = 0
        for turn in turns:
            amount = max(0, min(segment.end, turn["end"]) - max(segment.start, turn["start"]))
            if amount > overlap:
                overlap, best = amount, turn["speaker"]
        aligned.append({"start": segment.start, "end": segment.end, "text": segment.text,
                        "language": segment.language, "speaker": best or "SPEAKER_00"})
    return aligned
