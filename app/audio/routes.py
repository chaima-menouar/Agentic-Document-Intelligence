import importlib.util
import logging
import os
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from .service import MAX_SECONDS, MAX_TEXT, summarize_transcript, transcribe_audio

router = APIRouter(prefix="/api/audio")
MAX_AUDIO_BYTES = 4 * 1024 * 1024


def audio_available():
    return os.environ.get("ADI_AUDIO_ENABLED", "0") == "1" and importlib.util.find_spec("faster_whisper") is not None


@router.get('/capabilities')
def capabilities():
    return {"transcription": audio_available(), "max_bytes": MAX_AUDIO_BYTES, "max_seconds": MAX_SECONDS, "summary": "extractive", "translation": False, "speaker_diarization": False}


@router.post('/transcribe')
def transcribe(file: UploadFile = File(...), language: Literal['auto','en','fr','ar','es','de'] = Form('auto')):
    if not audio_available():
        raise HTTPException(503, 'Audio-file transcription is not enabled on this server. Use live dictation or paste a transcript.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.mp3','.wav','.m4a','.mp4','.webm','.ogg','.flac'}:
        raise HTTPException(400, 'Choose MP3, WAV, M4A, MP4, WebM, OGG or FLAC audio.')
    payload = file.file.read(MAX_AUDIO_BYTES + 1)
    if len(payload) > MAX_AUDIO_BYTES:
        raise HTTPException(413, 'Audio files must be 4 MB or smaller.')
    if not payload:
        raise HTTPException(400, 'The audio file is empty.')
    with tempfile.TemporaryDirectory(prefix='clario-audio-') as directory:
        path = Path(directory) / ('clip' + suffix)
        path.write_bytes(payload)
        try:
            return transcribe_audio(str(path), None if language == 'auto' else language)
        except HTTPException:
            raise
        except Exception:
            logging.getLogger(__name__).exception('Audio transcription failed')
            raise HTTPException(503, 'Transcription is unavailable. The speech model may still be downloading; retry shortly or use live dictation.')


class Transcript(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)


@router.post('/summary')
def summary(data: Transcript):
    if not data.text.strip():
        raise HTTPException(400, 'Add a transcript first.')
    return summarize_transcript(data.text.strip())
