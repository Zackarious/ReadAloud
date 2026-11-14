#!/usr/bin/env bash
# build_appimage.sh - Builds a standalone Linux x86_64 AppImage for ReadAloud
# and creates a multi-volume split zip to adhere to GitHub release upload limits.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION="1.8.19"
APP_NAME="ReadAloud"
APPDIR="${REPO_ROOT}/build-appimage/AppDir"
DIST_DIR="${REPO_ROOT}/dist"
APPIMAGE_NAME="${APP_NAME}-${VERSION}-linux-x86_64.AppImage"
ZIP_SPLIT_NAME="${APPIMAGE_NAME}.zip"

echo "=== Building ${APP_NAME} v${VERSION} Linux x86_64 AppImage ==="

# 1. Clean previous builds
rm -rf "${REPO_ROOT}/build-appimage"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share"
mkdir -p "${APPDIR}/usr/lib"
mkdir -p "${DIST_DIR}"

# 2. Compile GLib GResource Bundle
echo "[1/7] Compiling GLib resource bundle..."
glib-compile-resources "${REPO_ROOT}/src/readaloud.gresource.xml" \
    --target="${REPO_ROOT}/src/readaloud.gresource" \
    --sourcedir="${REPO_ROOT}/src"

# 3. Configure and install application into AppDir
echo "[2/7] Configuring Meson build for AppDir..."
BUILD_MESON="${REPO_ROOT}/build-appimage/meson-build"
meson setup "${BUILD_MESON}" "${REPO_ROOT}" --prefix=/usr --buildtype=release
ninja -C "${BUILD_MESON}"
DESTDIR="${APPDIR}" ninja -C "${BUILD_MESON}" install

# 4. Setup Python Virtualenv with required runtime dependencies
echo "[3/7] Setting up isolated Python runtime..."
VENV_DIR="${APPDIR}/usr/lib/readaloud/venv"
python3 -m venv --system-site-packages "${VENV_DIR}"

echo "[4/7] Installing Piper and speech modules into private runtime..."
"${VENV_DIR}/bin/pip" install --no-cache-dir \
    "piper-tts>=1.2.0" \
    "onnxruntime>=1.16.0" \
    "sounddevice>=0.4.6" \
    "numpy>=1.24.0" \
    "pathvalidate>=3.3.1" || true

# Strip unused files from venv
rm -rf "${VENV_DIR}/include" "${VENV_DIR}/share"
find "${VENV_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${VENV_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

# 5. Bundle offline neural voice models
echo "[5/7] Bundling Piper offline neural voice models..."
MODELS_DEST="${APPDIR}/usr/share/readaloud/models"
mkdir -p "${MODELS_DEST}"
if [ -d "${REPO_ROOT}/models" ]; then
    cp -r "${REPO_ROOT}/models/"* "${MODELS_DEST}/"
fi

# 6. Create AppRun and Desktop Integration
echo "[6/7] Creating AppRun and desktop integration files..."
cat << 'EOF' > "${APPDIR}/AppRun"
#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

export APPDIR="${HERE}"
export PATH="${HERE}/usr/bin:${HERE}/usr/lib/readaloud/venv/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${HERE}/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export GSETTINGS_SCHEMA_DIR="${HERE}/usr/share/glib-2.0/schemas:${GSETTINGS_SCHEMA_DIR}"

# Locate Python site-packages dynamically inside the bundle
PY_SITE=$(find "${HERE}/usr/lib/readaloud/venv/lib" -maxdepth 2 -type d -name "site-packages" | head -n 1)
if [ -n "$PY_SITE" ]; then
    export PYTHONPATH="${PY_SITE}:${HERE}/usr/share/readaloud:${PYTHONPATH}"
else
    export PYTHONPATH="${HERE}/usr/share/readaloud:${PYTHONPATH}"
fi

# Ensure Piper espeak data path is discovered
ESPEAK_DIR=$(find "${PY_SITE}" -type d -name "espeak-ng-data" 2>/dev/null | head -n 1)
if [ -n "$ESPEAK_DIR" ]; then
    export ESPEAK_DATA_PATH="$ESPEAK_DIR"
fi

exec "${HERE}/usr/bin/readaloud" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

# Copy desktop metadata and generate PNG icon for AppDir
cp "${REPO_ROOT}/data/im.zackarious.ReadAloud.desktop" "${APPDIR}/im.zackarious.ReadAloud.desktop"
cp "${REPO_ROOT}/data/im.zackarious.ReadAloud.desktop" "${APPDIR}/readaloud.desktop"
cp "${REPO_ROOT}/data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg" "${APPDIR}/im.zackarious.ReadAloud.svg"

# Generate 256x256 PNG for .DirIcon (appimagetool requires PNG .DirIcon)
python3 -c "import gi; gi.require_version('GdkPixbuf', '2.0'); from gi.repository import GdkPixbuf; pb = GdkPixbuf.Pixbuf.new_from_file_at_scale('${REPO_ROOT}/data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg', 256, 256, True); pb.savev('${APPDIR}/im.zackarious.ReadAloud.png', 'png', [], []); pb.savev('${APPDIR}/.DirIcon', 'png', [], [])" || true

# 7. Package AppImage using appimagetool
echo "[7/7] Generating AppImage..."
if ! command -v appimagetool >/dev/null 2>&1; then
    echo "Downloading appimagetool..."
    curl -sSL -o /tmp/appimagetool "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x /tmp/appimagetool
    APPIMAGETOOL="/tmp/appimagetool"
else
    APPIMAGETOOL="appimagetool"
fi

ARCH=x86_64 "${APPIMAGETOOL}" --no-appstream "${APPDIR}" "${DIST_DIR}/${APPIMAGE_NAME}" || {
    echo "Notice: Falling back to appimagetool extraction mode..."
    (
        cd /tmp
        "${APPIMAGETOOL}" --appimage-extract
    )
    ARCH=x86_64 /tmp/squashfs-root/AppRun --no-appstream "${APPDIR}" "${DIST_DIR}/${APPIMAGE_NAME}"
}

chmod +x "${DIST_DIR}/${APPIMAGE_NAME}"
echo "=== Created AppImage at ${DIST_DIR}/${APPIMAGE_NAME} ==="

# 8. Create Multi-Volume Split Files (1800 MB slices to bypass GitHub release limit)
echo "=== Splitting AppImage into multi-volume parts (${APPIMAGE_NAME}.001, .002) ==="
(
    cd "${DIST_DIR}"
    rm -f "${APPIMAGE_NAME}."*
    split -b 1800M -a 3 --numeric-suffixes=1 "${APPIMAGE_NAME}" "${APPIMAGE_NAME}."
    SIZE_BYTES=$(stat -c%s "${APPIMAGE_NAME}")
    if [ "${SIZE_BYTES}" -ge 2000000000 ]; then
        echo "AppImage is ${SIZE_BYTES} bytes (> 2 GB limit). Retaining split volumes for GitHub Release."
        rm -f "${APPIMAGE_NAME}"
    fi
)

# 9. Build Standalone AppImage Launcher (with multi-slice auto-downloader)
echo "=== Building Standalone AppImage Launcher ==="
bash "${SCRIPT_DIR}/build_appimage_launcher.sh"

ls -lh "${DIST_DIR}/${APPIMAGE_NAME}"* || true
echo "=== Linux x86_64 AppImage packaging complete! ==="
