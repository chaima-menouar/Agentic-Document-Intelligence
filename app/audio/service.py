from __future__ import annotations

import os
import re
import threading
from collections import Counter

MAX_SECONDS = 90
MAX_TEXT = 20000
_lock = threading.Lock()
_model = None


def transcribe_audio(path: str, language: str | None = None) -> dict:
    """Decode at most 90 seconds, serialize CPU inference and drop raw audio afterward."""
    import av
    import numpy as np
    from fastapi import HTTPException
    from faster_whisper import WhisperModel

    samples = []
    length = 0
    try:
        with av.open(path) as container:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            for frame in container.decode(audio=0):
                for converted in resampler.resample(frame):
                    values = converted.to_ndarray().flatten()
                    length += len(values)
                    if length > MAX_SECONDS * 16000:
                        raise HTTPException(413, "Audio clips must be 90 seconds or shorter.")
                    samples.append(values)
            for converted in resampler.resample(None):
                values = converted.to_ndarray().flatten()
                length += len(values)
                if length > MAX_SECONDS * 16000:
                    raise HTTPException(413, "Audio clips must be 90 seconds or shorter.")
                samples.append(values)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "This file could not be decoded as audio. Try MP3, WAV, M4A or WebM.") from exc
    if length < 1600:
        raise HTTPException(422, "The audio clip is empty or too short.")
    if not _lock.acquire(blocking=False):
        raise HTTPException(503, "Audio transcription is busy. Please retry shortly.")
    try:
        global _model
        if _model is None:
            _model = WhisperModel(os.environ.get("ADI_WHISPER_MODEL", "tiny"), device="cpu", compute_type="int8", cpu_threads=2, num_workers=1)
        audio = np.concatenate(samples).astype(np.float32) / 32768.0
        segments, info = _model.transcribe(audio, language=language, beam_size=1, vad_filter=True, condition_on_previous_text=False)
        rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments if s.text.strip()]
        text = " ".join(s["text"] for s in rows)
        return {"text": text, "segments": rows, "language": info.language, "duration_seconds": round(length / 16000, 2), "engine": "whisper-tiny-cpu"}
    finally:
        _lock.release()


def summarize_transcript(text: str) -> dict:
    """Extract exact lines; never invent decisions, owners or deadlines."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?؟])\s+|\n+", text) if len(s.strip()) >= 8]
    sentences = list(dict.fromkeys(sentences))
    tokens = lambda s: re.findall(r"[^\W\d_]{4,}", s.lower())
    counts = Counter(w for s in sentences for w in set(tokens(s)))
    ranked = sorted(range(len(sentences)), key=lambda i: sum(counts[w] for w in set(tokens(sentences[i]))) / max(1, len(tokens(sentences[i])))**.5, reverse=True)
    selected = sorted(ranked[:5])
    questions = [s for s in sentences if s.endswith(('?', '؟')) or re.match(r'(?i)^(what|when|where|why|how|can|could|does|is|are|which|who|quel|quelle|quand|comment|pourquoi|est-ce)\b', s)]
    actions = [s for s in sentences if re.search(r'(?i)\b(will|must|need to|action item|next step|todo|doit|devons|à faire|prochaine étape)\b', s)]
    return {"summary": [sentences[i] for i in selected], "action_candidates": actions[:8], "questions": questions[-8:], "method": "extractive", "note": "Exact transcript excerpts. Review possible actions; owners and dates are not inferred."}
