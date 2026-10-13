# Production deployment

The React + FastAPI application can run as one Docker service. The image builds the Vite frontend, installs the Python retrieval/OCR stack, and serves both UI and API from Uvicorn.

## Vercel Hobby (hosted demo)

Live demo: https://agentic-document-intelligence.vercel.app/

Import this repository on Vercel using the **Services** application preset and the repository root. `vercel.json` routes UI and API traffic to a single container service built from `Dockerfile.vercel`. This image installs CPU-only PyTorch and includes Tesseract. GitHub commits trigger deployments automatically. No paid LLM API is required.

The 13 October 2026 deployment passed a small PDF upload/indexing test and a cited answer test. This is a deployment smoke test, not a multi-document quality benchmark.

Vercel instances can restart or scale independently. The current process-local workspace is temporary and is not durable or shared across instances. After the backend reports a missing workspace, the Assistant clears stale results and asks for another upload while keeping the question. Export useful answers from Activity before leaving. Persistent multi-instance sessions require external storage and are not implemented in this demo.

## Render

Create a new Blueprint from this repository and select the production branch. Render detects `render.yaml`, builds `Dockerfile`, and checks `/api/health`. The account used for the demo required card verification even on the Free plan, so the published demo uses Vercel instead.

No paid LLM API is required: the default generator is offline/extractive. Optional local-LLM mode expects `ADI_LOCAL_LLM_URL` and needs a separately reachable compatible endpoint.

## Release test

Upload a small English text PDF, ask one answerable question and one unsupported question, open a citation source, and verify the unsupported question abstains rather than inventing evidence. Then test a scanned PDF with OCR enabled.

## Runtime constraints

Workspaces are ephemeral and stored on the service filesystem. A restart clears uploads and history. Run one worker because the session registry is process-local. CPU-only embedding, NLI, reranking, and OCR can be slow on small instances; dense retrieval plus the offline generator is the safest demo configuration.
