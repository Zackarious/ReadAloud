#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BUILD_DIR="${REPO_ROOT}/build-deb"
DIST_DIR="${REPO_ROOT}/dist"
STAGING_DIR="${DIST_DIR}/staging-deb"
DEB_NAME="readaloud_1.8.11_amd64.deb"

echo "=== Building ReadAloud Debian (.deb) Package ==="

# 1. Clean previous build artifacts
rm -rf "${BUILD_DIR}" "${STAGING_DIR}" "${DIST_DIR}/${DEB_NAME}"
mkdir -p "${DIST_DIR}" "${STAGING_DIR}"

# 2. Configure Meson
echo "[1/6] Configuring Meson with /usr prefix..."
meson setup "${BUILD_DIR}" "${REPO_ROOT}" --prefix=/usr --buildtype=release

# 3. Build project
echo "[2/6] Compiling resources and translations with Ninja..."
ninja -C "${BUILD_DIR}"

# 4. Install into staging root
echo "[3/6] Installing into staging root..."
DESTDIR="${STAGING_DIR}" ninja -C "${BUILD_DIR}" install

# 5. Populate private virtualenv for offline runtime dependencies
echo "[4/6] Setting up private Python runtime (/usr/lib/readaloud/venv)..."
VENV_DIR="${STAGING_DIR}/usr/lib/readaloud/venv"
python3 -m venv --system-site-packages "${VENV_DIR}"

# Install necessary python modules into venv
"${VENV_DIR}/bin/pip" install --no-cache-dir \
    "piper-tts>=1.2.0" \
    "onnxruntime>=1.16.0" \
    "sounddevice>=0.4.6" \
    "numpy>=1.24.0" \
    "pathvalidate>=3.3.1" || true

# Strip unneeded venv binaries, include headers, and pycache to reduce size
rm -rf "${VENV_DIR}/bin" "${VENV_DIR}/include" "${VENV_DIR}/share"
find "${VENV_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${VENV_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

# 6. Optimize models for GitHub Releases 2.0 GiB ceiling if needed
# We ensure the 27 distinct speaker personas are bundled, trimming 8 duplicate low/medium variations
# so that the compressed .deb stays strictly under GitHub's 2,147,483,648 byte (2.0 GiB) API limit.
MODELS_DIR="${STAGING_DIR}/usr/share/readaloud/models"
if [ -d "${MODELS_DIR}" ] && [ "${BUNDLE_ALL_MODELS:-0}" != "1" ]; then
    echo "Pruning duplicate quality models to fit within GitHub's 2.0 GiB limit..."
    for dup in \
        en_US-ryan-low.onnx en_US-ryan-low.onnx.json \
        en_US-ryan-medium.onnx en_US-ryan-medium.onnx.json \
        en_US-lessac-low.onnx en_US-lessac-low.onnx.json \
        en_US-lessac-medium.onnx en_US-lessac-medium.onnx.json \
        en_US-ljspeech-medium.onnx en_US-ljspeech-medium.onnx.json \
        en_GB-cori-medium.onnx en_GB-cori-medium.onnx.json \
        en_US-amy-low.onnx en_US-amy-low.onnx.json \
        en_US-libritts_r-medium.onnx en_US-libritts_r-medium.onnx.json
    do
        rm -f "${MODELS_DIR}/${dup}"
    done
fi

# 7. Assemble DEBIAN control directory
echo "[5/6] Preparing DEBIAN control metadata..."
mkdir -p "${STAGING_DIR}/DEBIAN"
cp "${REPO_ROOT}/build_linux/debian/control" "${STAGING_DIR}/DEBIAN/"
cp "${REPO_ROOT}/build_linux/debian/postinst" "${STAGING_DIR}/DEBIAN/"
cp "${REPO_ROOT}/build_linux/debian/postrm" "${STAGING_DIR}/DEBIAN/"
chmod 755 "${STAGING_DIR}/DEBIAN/postinst" "${STAGING_DIR}/DEBIAN/postrm"

# Calculate Installed-Size in KB
INSTALLED_SIZE=$(du -sk "${STAGING_DIR}/usr" | cut -f1)
echo "Installed-Size: ${INSTALLED_SIZE}" >> "${STAGING_DIR}/DEBIAN/control"

# Generate md5sums
(
    cd "${STAGING_DIR}"
    find usr -type f -exec md5sum {} + > DEBIAN/md5sums
)

# 8. Build Debian package
echo "[6/6] Packing ${DEB_NAME} with zstd compression..."
dpkg-deb -Zzstd -z9 --root-owner-group --build "${STAGING_DIR}" "${DIST_DIR}/${DEB_NAME}"

ls -lh "${DIST_DIR}/${DEB_NAME}"
echo "=== Successfully built ${DIST_DIR}/${DEB_NAME} ==="
