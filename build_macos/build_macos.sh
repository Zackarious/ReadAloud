#!/usr/bin/env bash
# build_macos.sh - Assembles ReadAloud.app Universal macOS bundle
# and creates a multi-volume split zip to bypass GitHub upload limits.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION="1.8.17"
APP_NAME="ReadAloud"
BUILD_DIR="${REPO_ROOT}/build-macos"
APP_BUNDLE="${BUILD_DIR}/${APP_NAME}.app"
DIST_DIR="${REPO_ROOT}/dist"
ZIP_PREFIX="${APP_NAME}-${VERSION}-macos-universal.zip"

echo "=== Building ${APP_NAME} v${VERSION} macOS Universal Application ==="

# 1. Clean previous build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"
mkdir -p "${DIST_DIR}"

# 2. Compile GLib resource bundle
if command -v glib-compile-resources >/dev/null 2>&1; then
    echo "[1/6] Compiling GLib resource bundle..."
    glib-compile-resources "${REPO_ROOT}/src/readaloud.gresource.xml" \
        --target="${REPO_ROOT}/src/readaloud.gresource" \
        --sourcedir="${REPO_ROOT}/src"
fi

# 3. Create Info.plist
echo "[2/6] Generating macOS Info.plist..."
cat << EOF > "${APP_BUNDLE}/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>ReadAloud</string>
    <key>CFBundleIconFile</key>
    <string>ReadAloud</string>
    <key>CFBundleIdentifier</key>
    <string>im.zackarious.ReadAloud</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>ReadAloud</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
</dict>
</plist>
EOF

echo "APPL????" > "${APP_BUNDLE}/Contents/PkgInfo"

# 4. Copy application source, resources, and models
echo "[3/6] Copying application code and resources..."
cp -r "${REPO_ROOT}/src" "${APP_BUNDLE}/Contents/Resources/"

if [ -f "${REPO_ROOT}/src/readaloud.gresource" ]; then
    cp "${REPO_ROOT}/src/readaloud.gresource" "${APP_BUNDLE}/Contents/Resources/"
fi

# Copy models
if [ -d "${REPO_ROOT}/models" ]; then
    echo "[4/6] Bundling offline neural voice models..."
    cp -r "${REPO_ROOT}/models" "${APP_BUNDLE}/Contents/Resources/"
fi

# Copy icon if available
if [ -f "${REPO_ROOT}/data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg" ]; then
    cp "${REPO_ROOT}/data/icons/hicolor/scalable/apps/im.zackarious.ReadAloud.svg" "${APP_BUNDLE}/Contents/Resources/ReadAloud.svg"
fi

# 5. Create launcher script
echo "[5/6] Creating macOS launcher executable..."
cat << 'EOF' > "${APP_BUNDLE}/Contents/MacOS/ReadAloud"
#!/usr/bin/env bash
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTENTS_DIR="$(cd "${SELF_DIR}/.." && pwd)"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

export PATH="/usr/local/bin:/opt/homebrew/bin:${PATH}"
export PYTHONPATH="${RESOURCES_DIR}:${RESOURCES_DIR}/src:${PYTHONPATH:-}"

# Check for Homebrew or system python
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PY_BIN="/opt/homebrew/bin/python3"
elif [ -x "/usr/local/bin/python3" ]; then
    PY_BIN="/usr/local/bin/python3"
else
    PY_BIN="python3"
fi

exec "${PY_BIN}" -m src.main 1.8.17 "$@"
EOF
chmod +x "${APP_BUNDLE}/Contents/MacOS/ReadAloud"

# 6. Create multi-volume split zip using 7z (1800 MB slices)
echo "[6/6] Creating macOS Universal multi-volume split zip (${ZIP_PREFIX}.001, .002)..."
(
    cd "${BUILD_DIR}"
    rm -f "${DIST_DIR}/${ZIP_PREFIX}"*
    7z a -tzip -v1800m "${DIST_DIR}/${ZIP_PREFIX}" "${APP_NAME}.app"
)

ls -lh "${DIST_DIR}/${ZIP_PREFIX}"* || true
echo "=== macOS Universal split packaging complete! ==="
