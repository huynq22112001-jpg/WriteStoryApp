# ADR-004: Minimum macOS version

- Status: deferred; minimum version is not established.
- Date: 2026-10-03.
- Context: WriteStoryApp targets macOS WKWebView, and S08 requires testing the oldest supported OS version and its built-in Vietnamese Telex/VNI input methods.

## Decision

Do not claim a minimum macOS version until a built app has been tested on that release and the IME checklist passes on its WKWebView. The current Windows host cannot provide this evidence. Keep the release minimum unset in product documentation; choose and record a version after testing candidate macOS versions on supported hardware or VMs.

## Required evidence

Record macOS version, architecture, WKWebView/WebKit version, Telex and VNI results, app startup, and installer/signing outcome in the [manual IME checklist](../tests/manual/ime-checklist.md) and release record.
