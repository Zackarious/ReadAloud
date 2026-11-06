#!/usr/bin/env python3
"""build_arm64_portable.py - Constructs a standalone portable Windows ARM64 bundle
for ReadAloud and packages it into a multi-volume split zip to bypass GitHub's 2.0 GiB limit.
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess
from pathlib import Path

VERSION = "1.8.14"
APP_NAME = "ReadAloud"
REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
ARM64_BUNDLE_DIR = REPO_ROOT / "build-arm64" / "ReadAloud-windows-arm64"
ZIP_PREFIX = f"{APP_NAME}-{VERSION}-windows-arm64-portable.zip"

PYTHON_ARM64_URL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-arm64.zip"


def log(msg):
    print(f"[build_arm64] {msg}", flush=True)


def ensure_clean_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path):
    log(f"Downloading {url} -> {dest}...")
    urllib.request.urlretrieve(url, dest)


def setup_arm64_runtime():
    ensure_clean_dir(ARM64_BUNDLE_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download & extract Python ARM64 embeddable package
    temp_zip = REPO_ROOT / "build-arm64" / "python-embed-arm64.zip"
    if not temp_zip.exists():
        download_file(PYTHON_ARM64_URL, temp_zip)

    log("Extracting Windows ARM64 embeddable Python...")
    with zipfile.ZipFile(temp_zip, "r") as zf:
        zf.extractall(ARM64_BUNDLE_DIR)

    # Enable site-packages in python312._pth
    pth_files = list(ARM64_BUNDLE_DIR.glob("*._pth"))
    for pth in pth_files:
        content = pth.read_text(encoding="utf-8")
        if "#import site" in content:
            content = content.replace("#import site", "import site\n.\nlib\nsite-packages")
            pth.write_text(content, encoding="utf-8")
            log(f"Configured {pth.name} for site-packages and local imports")

    # 2. Compile and copy GLib resources
    gresource_file = REPO_ROOT / "src" / "readaloud.gresource"
    if not gresource_file.exists():
        log("Compiling GLib resource bundle...")
        subprocess.run(
            ["glib-compile-resources", "src/readaloud.gresource.xml",
             "--target=src/readaloud.gresource", "--sourcedir=src"],
            cwd=str(REPO_ROOT),
            check=False,
        )

    # 3. Copy application source
    log("Copying application source code...")
    src_dest = ARM64_BUNDLE_DIR / "src"
    shutil.copytree(REPO_ROOT / "src", src_dest, dirs_exist_ok=True)

    # 4. Copy models
    models_src = REPO_ROOT / "models"
    models_dest = ARM64_BUNDLE_DIR / "models"
    if models_src.exists():
        log("Bundling offline neural voice models...")
        shutil.copytree(models_src, models_dest, dirs_exist_ok=True)

    # 5. Copy shims if available
    shims = ["onnxruntime_shim", "espeakbridge_shim"]
    for shim in shims:
        s_src = REPO_ROOT / "build_windows" / shim
        if s_src.exists():
            shutil.copytree(s_src, ARM64_BUNDLE_DIR / shim, dirs_exist_ok=True)

    # 6. Create Windows ARM64 launcher scripts
    log("Creating Windows ARM64 portable launchers...")
    launcher_cmd = ARM64_BUNDLE_DIR / "ReadAloud.cmd"
    launcher_cmd.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "cd /d \"%~dp0\"\r\n"
        "set PYTHONHOME=%~dp0\r\n"
        "set PYTHONPATH=%~dp0;%~dp0\\src;%PYTHONPATH%\r\n"
        "set PATH=%~dp0;%~dp0\\bin;%PATH%\r\n"
        "python.exe -m src.main 1.8.14 %*\r\n"
        "if errorlevel 1 pause\r\n",
        encoding="utf-8",
    )

    launcher_vbs = ARM64_BUNDLE_DIR / "ReadAloud-Silent.vbs"
    vbs_content = (
        'Set WshShell = CreateObject("WScript.Shell")\r\n'
        'Set fso = CreateObject("Scripting.FileSystemObject")\r\n'
        'dir = fso.GetParentFolderName(WScript.ScriptFullName)\r\n'
        'WshShell.Run Chr(34) & dir & "\\ReadAloud.cmd" & Chr(34), 0, False\r\n'
    )
    launcher_vbs.write_text(vbs_content, encoding="utf-8")

    if (REPO_ROOT / "build_windows" / "ReadAloud.ico").exists():
        shutil.copy(REPO_ROOT / "build_windows" / "ReadAloud.ico", ARM64_BUNDLE_DIR / "ReadAloud.ico")

    # 7. Create multi-volume split zip using 7z
    log(f"Creating multi-volume split zip ({ZIP_PREFIX}.001, .002)...")
    out_zip = DIST_DIR / ZIP_PREFIX
    # Remove older slices if any
    for existing in DIST_DIR.glob(f"{ZIP_PREFIX}*"):
        existing.unlink()

    cmd = [
        "7z", "a", "-tzip", "-v1800m",
        str(out_zip),
        str(ARM64_BUNDLE_DIR),
    ]
    log(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    log("=== Windows ARM64 portable split package ready! ===")
    for f in DIST_DIR.glob(f"{ZIP_PREFIX}*"):
        log(f"  Asset: {f.name} ({f.stat().st_size / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    setup_arm64_runtime()
