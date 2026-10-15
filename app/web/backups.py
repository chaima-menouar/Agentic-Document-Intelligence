"""Portable, bounded workspace snapshots. Never extract or load archived indexes."""
import io
import json
import zipfile
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field
from app.models.schemas import AgenticRAGAnswer

MAX_ARCHIVE = 4 * 1024 * 1024
MAX_METADATA = 1024 * 1024


class SavedAnswer(AgenticRAGAnswer):
    id: str = Field(pattern=r'^[a-f0-9]{16}$')
    latency_seconds: float = Field(ge=0, allow_inf_nan=False)
    settings: dict = Field(default_factory=dict)


class SavedFeedback(BaseModel):
    rating: Literal['useful', 'needs_review', 'incorrect']
    note: str = Field(default='', max_length=2000)


class Manifest(BaseModel):
    format: Literal['clario-workspace']
    version: Literal[1]
    history: list[SavedAnswer] = Field(default_factory=list, max_length=50)
    feedback: dict[str, SavedFeedback] = Field(default_factory=dict)
    transcript: str = Field(default='', max_length=20000)


def encode_snapshot(ws, transcript):
    manifest = Manifest(format='clario-workspace', version=1, history=ws.history, feedback=ws.feedback, transcript=transcript)
    metadata = manifest.model_dump_json().encode()
    if len(metadata) > MAX_METADATA:
        raise ValueError('Answer history is too large for a backup. Export the session separately.')
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('workspace.json', metadata)
        for doc in ws.result.documents if ws.result else []:
            archive.writestr('documents/' + doc.filename, (ws.directory / 'uploads' / doc.filename).read_bytes())
    data = output.getvalue()
    if len(data) > MAX_ARCHIVE:
        raise ValueError('Backup exceeds 4 MB. Export the session and keep your original PDFs separately.')
    return data


def decode_snapshot(data, pdf_limit, total_limit):
    if len(data) > MAX_ARCHIVE:
        raise ValueError('Backup exceeds 4 MB.')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if not 1 <= len(entries) <= 11 or len(names) != len(set(names)) or names.count('workspace.json') != 1:
            raise ValueError('Expected one workspace manifest and up to 10 PDFs.')
        if sum(e.file_size for e in entries) > total_limit + MAX_METADATA:
            raise ValueError('Expanded backup exceeds the workspace size limit.')
        payloads = []
        manifest = None
        total = 0
        for entry in entries:
            name = entry.filename
            if entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError('Encrypted or unsupported backups cannot be restored.')
            if name == 'workspace.json':
                if entry.file_size > MAX_METADATA:
                    raise ValueError('Backup manifest is too large.')
                manifest = Manifest.model_validate_json(archive.read(entry))
                continue
            path = PurePosixPath(name)
            if len(path.parts) != 2 or path.parts[0] != 'documents' or '\\' in name or not path.name.lower().endswith('.pdf'):
                raise ValueError('Backup contains an unexpected file path.')
            total += entry.file_size
            if entry.file_size > pdf_limit or total > total_limit:
                raise ValueError('PDFs exceed the workspace size limit.')
            payload = archive.read(entry)
            if not payload.startswith(b'%PDF-'):
                raise ValueError('Backup contains an invalid PDF.')
            # prepare_uploaded_pdfs adds this prefix again, so strip exactly one.
            filename = path.name
            if len(filename) > 4 and filename[:3].isdigit() and filename[3] == '_':
                filename = filename[4:]
            payloads.append((filename, payload))
        ids = [a.id for a in manifest.history]
        if len(ids) != len(set(ids)) or not set(manifest.feedback).issubset(ids):
            raise ValueError('Backup contains inconsistent answer history.')
        return payloads, manifest
