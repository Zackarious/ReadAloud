#!/usr/bin/env bash
# build_appimage_launcher.sh - Constructs the standalone AppImage launcher for ReadAloud
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION="1.8.19"
APP_NAME="ReadAloud"
LAUNCHER_APPDIR="${REPO_ROOT}/build-appimage-launcher/AppDir"
DIST_DIR="${REPO_ROOT}/dist"
APPIMAGE_NAME="${APP_NAME}-${VERSION}-linux-x86_64.AppImage"

echo "=== Building ${APP_NAME} v${VERSION} Standalone AppImage Launcher ==="

# 1. Clean previous build directory
rm -rf "${REPO_ROOT}/build-appimage-launcher"
mkdir -p "${LAUNCHER_APPDIR}/usr/bin"
mkdir -p "${LAUNCHER_APPDIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${DIST_DIR}"

# 2. Copy launcher script
cp "${SCRIPT_DIR}/appimage_launcher.py" "${LAUNCHER_APPDIR}/appimage_launcher.py"
chmod +x "${LAUNCHER_APPDIR}/appimage_launcher.py"

# 3. Create AppRun entrypoint
cat << 'APPRUN_EOF' > "${LAUNCHER_APPDIR}/AppRun"
#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

export APPDIR="${HERE}"
exec python3 "${HERE}/appimage_launcher.py" "$@"
APPRUN_EOF
chmod +x "${LAUNCHER_APPDIR}/AppRun"

# 4. Copy icons and desktop entry
cp "${REPO_ROOT}/data/im.zackarious.ReadAloud.desktop" "${LAUNCHER_APPDIR}/im.zackarious.ReadAloud.desktop"
cp "${REPO_ROOT}/data/im.zackarious.ReadAloud.desktop" "${LAUNCHER_APPDIR}/readaloud.desktop"
cp "${REPO_ROOT}/data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg" "${LAUNCHER_APPDIR}/im.zackarious.ReadAloud.svg"
cp "${REPO_ROOT}/data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg" "${LAUNCHER_APPDIR}/usr/share/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg"

# 5. Generate PNG icons for AppImage desktop and .DirIcon
python3 -c "import gi; gi.require_version('GdkPixbuf', '2.0'); from gi.repository import GdkPixbuf; pb = GdkPixbuf.Pixbuf.new_from_file_at_scale('${REPO_ROOT}/data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg', 256, 256, True); pb.savev('${LAUNCHER_APPDIR}/im.zackarious.ReadAloud.png', 'png', [], []); pb.savev('${LAUNCHER_APPDIR}/.DirIcon', 'png', [], [])" || true

# 6. Locate or download appimagetool
if [ -x "/tmp/appimagetool" ]; then
    APPIMAGETOOL="/tmp/appimagetool"
elif command -v appimagetool >/dev/null 2>&1; then
    APPIMAGETOOL="appimagetool"
else
    echo "Downloading appimagetool..."
    curl -sSL -o /tmp/appimagetool "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x /tmp/appimagetool
    APPIMAGETOOL="/tmp/appimagetool"
fi

# 7. Package AppImage
echo "Packaging standalone launcher AppImage..."
ARCH=x86_64 "${APPIMAGETOOL}" --no-appstream "${LAUNCHER_APPDIR}" "${DIST_DIR}/${APPIMAGE_NAME}" || {
    echo "Notice: Falling back to appimagetool extraction mode..."
    (
        cd /tmp
        "${APPIMAGETOOL}" --appimage-extract
    )
    ARCH=x86_64 /tmp/squashfs-root/AppRun --no-appstream "${LAUNCHER_APPDIR}" "${DIST_DIR}/${APPIMAGE_NAME}"
}

chmod +x "${DIST_DIR}/${APPIMAGE_NAME}"
echo "=== Created Standalone AppImage Launcher at ${DIST_DIR}/${APPIMAGE_NAME} ==="
ls -lh "${DIST_DIR}/${APPIMAGE_NAME}"
