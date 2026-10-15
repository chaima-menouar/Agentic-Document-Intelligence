# Workspace recovery — release stage 1

Clario server sessions are still temporary. This release adds a portable recovery
option; it does not claim account-based cloud persistence.

## User flow

In Documents or Settings, select **Download workspace backup**. Keep the ZIP
privately: it contains the original PDFs, the last 50 document answers and their
citations, answer feedback, and the current Audio Studio transcript.

To resume after expiration or a restart, select **Restore a backup**, choose the
ZIP and confirm replacement. PDFs are reprocessed and the index rebuilt. The
existing workspace remains intact if validation or indexing fails. Source links
use content-based document IDs, so restored citations still open the original PDF.
Imported answers are saved results, not fresh verification. Ask again to recheck.

The maximum compressed ZIP is 4 MiB, metadata 1 MiB, with at most 10 PDFs subject
to the deployed PDF limits. Download can be refused if history/PDFs exceed these
limits; in that case export the session JSON and retain the PDFs separately.
Audio recordings, generated audio notes, preferences and unsent questions are not
included. This is manual recovery, not autosave or multi-device synchronization.

## API

- POST /api/workspace/backup: JSON transcript and workspace_revision; returns ZIP.
- POST /api/workspace/restore: multipart file, X-ADI-Workspace revision; returns
  workspace and transcript. Both endpoints require X-ADI-Request: 1.

ZIP entries are read into bounded memory, never extracted. Paths, member counts,
uncompressed sizes, format/version, PDF signatures and answer schemas are checked.
No index, pickle, executable or model artifact is restored. A failed/stale restore
cannot replace a valid current workspace. Backups do not include session cookies.

## Remaining release gates

1. Connect a user-owned database/storage and authentication provider. This needs
   real project configuration, email delivery and tenant-isolation verification.
   Do not enable a cosmetic login screen or claim persistence before testing it.
2. Verify account recovery, logout, deletion and simultaneous-device conflicts.
3. Test microphone permission, live dictation and speech output on real Chrome,
   Safari/iOS and Android devices. Browser support is not universal.
4. Connect the user's n8n instance and exercise the workflow there.
5. Recheck mobile layout, keyboard navigation and loading/error states.

No paid service or new account was activated by this release.
