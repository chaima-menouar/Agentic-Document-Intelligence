# React document workspace

## Start in Codespaces

1. Stop the old Streamlit process with Ctrl+C.
2. `git switch v2-development`
3. `git pull --ff-only origin v2-development`
4. `bash scripts/run_web.sh`
5. Open port **8501**. The React page and Python API share this port.

Requires Python 3.12 and Node.js 22.12+ (or 20.19+). New containers install Node 22 through the devcontainer feature. In an existing Codespace, use `nvm install 22 && nvm use 22` if Node is missing or old. The launcher installs the Python dependencies, builds React, and starts the server. Tesseract with English language data must be installed for scanned documents, as in the existing container setup.

For subsequent launches without reinstalling/rebuilding:

```bash
python -m uvicorn app.web.api:app --host 0.0.0.0 --port 8501 --workers 1
```

Keep the forwarded Codespaces port private. This is a single-process local research app, not a public multi-user service. Browser sessions have separate temporary documents and history; workspaces expire after eight idle hours (cleaned on the next API request), when cleared, or on a normal server exit. Restarting the server loses history. A forced process kill may leave temporary `adi-react-*` folders for manual cleanup. Initial BGE/NLI/reranker model use requires a download; no paid API key is required. Local LLM mode requires a separate Ollama/LM Studio server; set `ADI_LOCAL_LLM_URL` on the Python server if it differs from `http://localhost:11434/v1`.

## Features

- PDF upload, optional local OCR, real BGE/FAISS indexing.
- Agentic questions scoped to one PDF or the full corpus.
- Dense/hybrid/reranked retrieval and semantic/lexical verification.
- Real answers, citations, original PDFs, extracted chunks, claim checks and recovery traces.
- Session activity, answer feedback and JSON export.
- Responsive charcoal/yellow UI with reduced-motion support.

Uploading a new batch **replaces** the previous workspace only after processing succeeds. No fake answers, sample metrics, external fonts, or paid APIs are used. The old Streamlit implementation remains available for compatibility but is not embedded in React.

## Development

Run Python as above, then in a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to the local Python server. Production uses `npm run build` and Python serves `frontend/dist`. Rebuild after changes to the frontend or the background image.

## Artwork

Active image: `frontend/public/background-documents-realistic.png`, generated with built-in imagegen. Prompt: photoreal paper documents linked to a graphite AI module and yellow glass verification indicator, charcoal backdrop, quiet negative space at left, no text or metallic spectacle. The previously proposed gold and abstract backgrounds are not used.
