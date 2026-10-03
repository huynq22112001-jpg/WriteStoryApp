# ADR-003: WebView2 installation and macOS DMG packaging

- Status: proposed; validate on a clean Windows VM and supported macOS hardware before release.
- Date: 2026-10-03.
- Context: Windows NSIS installer and portable builds need an explicit WebView2 runtime policy. The product also needs a documented macOS minimum, but this Windows host cannot establish compatibility with WKWebView versions.

## Decision

- NSIS requests Tauri's `offlineInstaller` WebView2 mode. Before publishing, build and install the NSIS artifact on a clean Windows 11 x64 VM with no WebView2 runtime, then verify the installer carries and installs the runtime without network access. This workspace has not yet verified that clean-machine scenario.
- Portable Windows builds require WebView2 already installed. A `fixedRuntime` portable variant remains a separate packaging decision because it adds a runtime payload and needs size and update measurements.
- Keep the existing Tauri target for macOS builds. The supported minimum macOS version is **not established** by this host; choose it only after testing the built app and IME checklist on the oldest supported macOS/WKWebView. Do not infer a version from the Windows build.

## DMG assembly

1. Build and sign the `.app` on macOS; sign the packaged backend with `tools/packaging/sign_macos_backend.sh` before the app bundle is assembled.
2. Create a staging directory containing `WriteStoryApp.app` and a symlink named `Applications` pointing to `/Applications`.
3. Create a compressed UDZO DMG from the staging directory with `hdiutil create`; mount it and verify both the app and Applications link before notarization/stapling and release.
4. Record the macOS version, architecture, WebKit version, signing/notarization result, DMG size, cold start-to-ready time, and idle memory in the release record.

## Evidence and open checks

- `desktop/src-tauri/tauri.conf.json` selects `offlineInstaller` for NSIS.
- No clean-machine Windows installer test or macOS test has been run from this Windows host.
- The minimum macOS version is tracked separately in [ADR-004](./ADR-004-macos-minimum.md).
