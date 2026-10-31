#!/usr/bin/env bash
# build.sh - Automated MSYS2 / Linux cross-check Windows Build Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== ReadAloud Windows Build Automation ==="

# 1. Compile GLib resources
if command -v glib-compile-resources >/dev/null 2>&1; then
    echo "-> Compiling GLib resource bundle..."
    glib-compile-resources src/readaloud.gresource.xml --target=src/readaloud.gresource --sourcedir=src
fi

# 2. Install requirements
echo "-> Installing Python dependencies..."
python3 -m pip install -r requirements-windows.txt

# 3. Run PyInstaller
echo "-> Packaging executable with PyInstaller..."
pyinstaller build_windows/ReadAloud.spec --clean -y

# 4. Post-build runtime enforcement
echo "-> Enforcing runtime dependencies..."
INTERNAL_DIR="dist/ReadAloud/_internal"
if [ -d "$INTERNAL_DIR" ]; then
    mkdir -p "$INTERNAL_DIR/piper"
    python3 -c "import piper, pathlib, shutil; src = pathlib.Path(piper.__file__).parent / 'espeak-ng-data'; dst = pathlib.Path('$INTERNAL_DIR/piper/espeak-ng-data'); shutil.copytree(src, dst, dirs_exist_ok=True) if src.is_dir() else None" 2>/dev/null || true
    python3 -c "import piper, pathlib, shutil; src = pathlib.Path(piper.__file__).parent / 'tashkeel'; dst = pathlib.Path('$INTERNAL_DIR/piper/tashkeel'); shutil.copytree(src, dst, dirs_exist_ok=True) if src.is_dir() else None" 2>/dev/null || true
fi

# 5. Copy models into dist folder
echo "-> Bundling voice models into dist/ReadAloud/models/..."
mkdir -p dist/ReadAloud/models
cp -ru models/* dist/ReadAloud/models/

if [ -f "build_windows/ReadAloud.ico" ]; then
    cp -u "build_windows/ReadAloud.ico" "dist/ReadAloud/"
fi

echo "=== Standalone executable ready at dist/ReadAloud/ReadAloud.exe ==="

# 6. Check for Inno Setup compiler
if command -v iscc >/dev/null 2>&1; then
    echo "-> Compiling Windows Installer with Inno Setup..."
    iscc build_windows/installer.iss
    echo "=== Windows Setup Installer created in dist/ ==="
fi
