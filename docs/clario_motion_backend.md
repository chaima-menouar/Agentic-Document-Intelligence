# Clario motion and backend reliability

The orange palette is retained. The document journey is an explicitly illustrative, four-stage interaction with pause/play and manual stage selection. Auto-advance pauses outside the viewport and in background tabs, and starts paused when reduced motion is requested. Pointer lighting does not run for touch input or reduced motion. Workspace screens animate on entry.

Backend changes:

- `GET /api/capabilities` exposes upload limits, OCR availability, whether a local model endpoint is configured, and temporary storage semantics. It does not probe or promise model availability.
- Workspace responses include an opaque `revision`. Upload/reset accept `X-ADI-Workspace`; questions accept `workspace_revision`. A mismatched revision returns a 409 before mutation or inference, protecting clients with stale tabs. Older clients without revisions remain compatible.
- Questions optionally accept `request_id`. Retrying the same payload and ID returns the original answer without rerunning inference, within the same workspace and retained 50-answer history. Reusing an ID for different input returns 409. IDs, feedback and cached answers are pruned together.
- The frontend retains a question request ID after a transport failure, refreshes on workspace conflict, and preserves the typed question. It gets upload limits from the backend and disables unconfigured local generation.
- Offline extraction can answer a `When` question from month/day or time evidence without requiring a year. Explicit year questions still require a year. This is a narrow baseline improvement, not an accuracy claim.

## Remaining limits

Sessions and idempotency records are still in process memory; PDFs and indexes are in temporary storage. A restart or routing to another instance can lose a workspace. Durable storage and a shared session store still require a separate deployment design. No database or paid provider was provisioned. n8n remains an importable manual health-check workflow, not a connected service.

## Verification

Run `python -m pytest tests/test_web_api.py tests/test_extractive_generator.py -q` and `npm run build --prefix frontend`. HTTP tests use deterministic retrieval fixtures and do not claim to evaluate semantic model quality. New regression cases cover stale uploads/reset/ask, retry deduplication, conflicting request IDs, configuration gating and month/day answers.
