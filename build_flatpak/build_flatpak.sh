#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== ReadAloud Flatpak Builder ==="
echo "Manifest: ${SCRIPT_DIR}/im.zackarious.ReadAloud.yaml"

cd "${SCRIPT_DIR}"

# Build and install locally for user testing
flatpak-builder --user --install --force-clean "${ROOT_DIR}/_flatpak_build" "${SCRIPT_DIR}/im.zackarious.ReadAloud.yaml"

echo "Build complete! You can run the Flatpak with:"
echo "flatpak run im.zackarious.ReadAloud"
