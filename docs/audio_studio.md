# Clario Audio Studio

## Delivered

- **Live dictation:** Web Speech API, when supported by the browser. Starts only after explicit user consent and a button click. The browser may send audio to its speech service. It is not guaranteed offline, multilingual quality varies, and it captures the microphone only.
- **Record/upload clips:** MediaRecorder or MP3/WAV/M4A/MP4/WebM/OGG/FLAC input. The FastAPI server decodes to mono 16 kHz and runs faster-whisper tiny with CPU int8. Raw temporary files are removed after success or error. Maximum 4 MB and 90 seconds; microphone recording stops at 85 seconds for overhead. The Vercel image predownloads the model during its build; other deployments may download it on first transcription.
- **Editable transcript:** 20,000 characters, retained across workspace tab changes in page memory. Refreshing loses it; export a JSON copy to keep it.
- **Document answers:** use a detected question or the transcript with the existing retriever, verification, citations, request IDs and workspace revision. Optional auto-answer watches finalized live dictation for question cues; it is approximate, debounced and processes one request at a time. Document retrieval currently works best in English.
- **Notes:** five ranked exact excerpts, possible action sentences and detected questions. It does not infer owners, deadlines or decisions. This is extractive summarization, not a fluent generative model.
- **Read aloud:** browser speech synthesis, explicit button, for English document answers. Speaking stops when leaving the audio panel.
- **n8n:** `integrations/n8n/transcript-summary.json`, a manual trigger, editable transcript and HTTP summary request. Import, edit transcript, execute. No n8n instance is connected or automatically activated, and the workflow sends the entered transcript to the Clario endpoint.

## Server

Install `requirements-audio.txt`, set `ADI_AUDIO_ENABLED=1`, optional `ADI_WHISPER_MODEL=tiny`. Vercel container includes these settings. `GET /api/audio/capabilities` reports feature availability and limits. `POST /api/audio/transcribe` accepts multipart `file` and `language` (`auto`, `en`, `fr`, `ar`, `es`, `de`). `POST /api/audio/summary` accepts `{"text":"..."}`. Mutating endpoints require `X-ADI-Request: 1` like the other app APIs. Model downloads require network access; availability is not a guarantee of model load success.

## Explicit boundaries

This is not full VoxTrace parity. No system/meeting-tab audio capture, diarization, real-time translation, full-duplex conversation, long-meeting processing, permanent storage or linked meeting accounts. The UI says so. No payment provider or paid API has been added. The Spline robot and orange palette remain.

## Validation

API tests cover summary grounding, validation, request headers, audio size/type/language limits, tempfile cleanup and disabled capability behavior. 24 targeted tests passed. Real transcription was separately smoke-tested on the public OpenAI Whisper `tests/jfk.flac` fixture, without private user audio. Microphone permission flows require a real user device; an automated test is not evidence that every browser supports live speech.
