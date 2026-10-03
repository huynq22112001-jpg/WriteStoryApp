# ADR-001: Shell desktop cho WriteStoryApp

- Status: decision deferred pending real IME evidence; Tauri remains the current implementation.
- Date: 2026-10-03.
- Context: S08 requires proving Vietnamese IME stability on Windows WebView2 and macOS WKWebView before committing to Tauri or moving to Electron.

## Evidence

- Tiptap editor spike runs in the FE and has automated tests for paragraph IDs and split/merge behavior.
- No manual IME checklist cells have been run. See [ime-checklist.md](../tests/manual/ime-checklist.md).
- Automated tests do not exercise OS-level composition events and cannot establish that either WebView avoids lost or duplicated Vietnamese characters.

## Decision and follow-up

Keep Tauri as the working shell while completing the R0 implementation. This is not a compatibility approval. Do not make the final shell choice until the checklist has real Windows WebView2 and macOS WKWebView results. If a reproducible lost/duplicated-character issue remains on WKWebView, compare the cost of Electron before proceeding with larger editor work.
