# Production deployment

The React + FastAPI application can run as one Docker service. The image builds the Vite frontend, installs the Python retrieval/OCR stack, and serves both UI and API from Uvicorn.

## Render

Create a new Blueprint from this repository and select the production branch. Render detects `render.yaml`, builds `Dockerfile`, and checks `/api/health`.

No paid LLM API is required: the default generator is offline/extractive. Optional local-LLM mode expects `ADI_LOCAL_LLM_URL` and needs a separately reachable compatible endpoint.

## Release test

Upload a small English text PDF, ask one answerable question and one unsupported question, open a citation source, and verify the unsupported question abstains rather than inventing evidence. Then test a scanned PDF with OCR enabled.

## Runtime constraints

Workspaces are ephemeral and stored on the service filesystem. A restart clears uploads and history. Run one worker because the session registry is process-local. CPU-only embedding, NLI, reranking, and OCR can be slow on small instances; dense retrieval plus the offline generator is the safest demo configuration.
