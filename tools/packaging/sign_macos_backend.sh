#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
RESOURCE_DIR="${WRITESTORY_BACKEND_RESOURCE_DIR:-$REPO_ROOT/desktop/src-tauri/resources/backend}"

if [[ -z "${MACOS_DEVELOPER_IDENTITY:-}" ]]; then
  echo "Set MACOS_DEVELOPER_IDENTITY to the Developer ID Application identity." >&2
  exit 2
fi
if [[ ! -d "$RESOURCE_DIR" ]]; then
  echo "Backend resources not found: $RESOURCE_DIR" >&2
  exit 2
fi
if ! command -v codesign >/dev/null 2>&1 || ! command -v file >/dev/null 2>&1; then
  echo "codesign and file are required (run this script on macOS)." >&2
  exit 2
fi

signed=0
while IFS= read -r -d '' candidate; do
  if file -b "$candidate" | grep -q 'Mach-O'; then
    codesign --force --options runtime --timestamp --sign "$MACOS_DEVELOPER_IDENTITY" "$candidate"
    signed=$((signed + 1))
  fi
done < <(find "$RESOURCE_DIR" -type f -print0)

if [[ "$signed" -eq 0 ]]; then
  echo "No Mach-O files found under $RESOURCE_DIR." >&2
  exit 1
fi
echo "Signed $signed Mach-O file(s)."
