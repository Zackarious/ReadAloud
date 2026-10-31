# -*- mode: python ; coding: utf-8 -*-
# ReadAloud.spec - PyInstaller Specification for Microsoft Windows
#
# Copyright 2025-2026 Walter Bernard / zackarious
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
from pathlib import Path

# Register MSYS2 MinGW64 / UCRT64 DLL directory if available on Windows
if sys.platform == "win32":
    prefix = os.environ.get("MINGW_PREFIX")
    candidates = []
    if prefix:
        candidates.append(Path(prefix) / "bin")
    candidates.extend([Path(r"C:\msys64\ucrt64\bin"), Path(r"C:\msys64\mingw64\bin")])
    for mingw_bin in candidates:
        if mingw_bin.is_dir() and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(mingw_bin))
                break
            except Exception:
                pass

block_cipher = None

spec_root = Path(SPECPATH).resolve()
repo_root = spec_root.parent

# Extra datas and binaries collection
extra_binaries = []
extra_datas = [
    (str(repo_root / "data" / "icons"), "data/icons"),
]

# Check for compiled gresource (encapsulate UI definitions to prevent Python namespace collision)
gresource_candidates = [
    repo_root / "src" / "readaloud.gresource",
    repo_root / "build" / "src" / "readaloud.gresource",
    repo_root / "build-dir" / "readaloud.gresource",
]
for candidate in gresource_candidates:
    if candidate.is_file():
        extra_datas.append((str(candidate), "."))
        extra_datas.append((str(candidate), "_internal"))
        break

# Harvest piper / espeak-ng-data and tashkeel
try:
    import piper
    piper_path = Path(piper.__file__).resolve().parent
    espeak_data = piper_path / "espeak-ng-data"
    if espeak_data.is_dir():
        extra_datas.append((str(espeak_data), "piper/espeak-ng-data"))
        extra_datas.append((str(espeak_data), "_internal/piper/espeak-ng-data"))
    tashkeel_data = piper_path / "tashkeel"
    if tashkeel_data.is_dir():
        extra_datas.append((str(tashkeel_data), "piper/tashkeel"))
        extra_datas.append((str(tashkeel_data), "_internal/piper/tashkeel"))
except Exception:
    pass

# Harvest PyGObject gi package tree from site-packages
try:
    import gi
    gi_path = Path(gi.__file__).resolve().parent
    extra_datas.append((str(gi_path), "gi"))
except Exception:
    pass

# MSYS2 MINGW64 environment detection
msys_prefix = os.environ.get("MINGW_PREFIX", "")
if not msys_prefix and sys.platform == "win32":
    py_dir = Path(sys.executable).parent
    if (py_dir.parent / "share" / "glib-2.0" / "schemas").is_dir():
        msys_prefix = str(py_dir.parent)
    elif Path(r"C:\msys64\ucrt64").is_dir():
        msys_prefix = r"C:\msys64\ucrt64"
    elif Path(r"C:\msys64\mingw64").is_dir():
        msys_prefix = r"C:\msys64\mingw64"

if msys_prefix:
    p = Path(msys_prefix)

    # 1. GSettings schemas
    schemas_dir = p / "share" / "glib-2.0" / "schemas"
    if schemas_dir.is_dir():
        extra_datas.append((str(schemas_dir), "share/glib-2.0/schemas"))

    # 2. Libadwaita & GTK4 styles / themes
    themes_dir = p / "share" / "themes"
    if themes_dir.is_dir():
        extra_datas.append((str(themes_dir), "share/themes"))

    # 3. GI Typelibs
    typelib_dir = p / "lib" / "girepository-1.0"
    if typelib_dir.is_dir():
        extra_datas.append((str(typelib_dir), "lib/girepository-1.0"))

    # 4. GdkPixbuf loaders
    pixbuf_dir = p / "lib" / "gdk-pixbuf-2.0"
    if pixbuf_dir.is_dir():
        extra_datas.append((str(pixbuf_dir), "lib/gdk-pixbuf-2.0"))

    # 5. GStreamer plugins
    gst_plugins_dir = p / "lib" / "gstreamer-1.0"
    if gst_plugins_dir.is_dir():
        extra_datas.append((str(gst_plugins_dir), "lib/gstreamer-1.0"))

    # 6. Icons
    icons_dir = p / "share" / "icons"
    if icons_dir.is_dir():
        extra_datas.append((str(icons_dir / "hicolor"), "share/icons/hicolor"))
        extra_datas.append((str(icons_dir / "Adwaita"), "share/icons/Adwaita"))

a = Analysis(
    [str(spec_root / "win_entrypoint.py")],
    pathex=[str(repo_root)],
    binaries=extra_binaries,
    datas=extra_datas,
    hiddenimports=[
        'gi',
        'gi.overrides',
        'gi.overrides.Gtk',
        'gi.overrides.GLib',
        'gi.overrides.Gio',
        'gi.overrides.GObject',
        'gi.overrides.Gdk',
        'gi.overrides.Pango',
        'gi.repository.Gtk',
        'gi.repository.Adw',
        'gi.repository.Gio',
        'gi.repository.GLib',
        'gi.repository.Gdk',
        'gi.repository.Pango',
        'gi.repository.Gst',
        'piper',
        'piper.voice',
        'piper_phonemize',
        'onnxruntime',
        'sounddevice',
        'numpy',
        'lameenc',
        'src.paths',
        'src.audio_backend',
        'src.main',
        'src.window',
        'src.reader',
        'src.pipervoice',
        'src.demos',
        'src.bubble',
        'src.vocxpo',
        'src.document_importer',
        'src.wikipedia_importer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Enforcement of Modern MSVC 2022 Runtime from System32 (eliminating 0xC0000005 crashes)
sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
msvc_overrides = {"msvcp140.dll", "msvcp140_1.dll", "vcruntime140.dll", "vcruntime140_1.dll"}
filtered_binaries = []
for dest_name, src_path, typecode in a.binaries:
    basename = os.path.basename(dest_name).lower()
    if basename in msvc_overrides:
        s32 = sys32 / basename
        if s32.is_file():
            filtered_binaries.append((dest_name, str(s32), typecode))
            continue
    filtered_binaries.append((dest_name, src_path, typecode))
a.binaries = filtered_binaries

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ReadAloud',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No black terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(spec_root / "ReadAloud.ico") if (spec_root / "ReadAloud.ico").is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ReadAloud',
)
