# paths.py
#
# Copyright 2025-2026 Walter Bernard / zackarious
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
from pathlib import Path

try:
    from gi.repository import GLib
    HAS_GLIB = True
except ImportError:
    HAS_GLIB = False


def is_frozen() -> bool:
    """Check whether the application is running inside a PyInstaller frozen bundle."""
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """
    Returns the root directory where application files are located.
    - In a frozen PyInstaller bundle: sys._MEIPASS or directory of sys.executable
    - In normal Python execution: the repository or package root
    """
    if is_frozen():
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        exe = str(sys.executable)
        if "\\" in exe:
            return Path(exe.rsplit("\\", 1)[0])
        return Path(exe).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_executable_dir() -> Path:
    """
    Returns the directory where the binary or script was launched from.
    - When frozen: directory containing ReadAloud.exe
    - When unfrozen: repository root
    """
    if is_frozen():
        exe = str(sys.executable)
        if "\\" in exe:
            return Path(exe.rsplit("\\", 1)[0])
        return Path(exe).resolve().parent
    return Path(__file__).resolve().parent.parent



def get_user_data_dir() -> Path:
    """
    Returns the user data directory for settings, custom models, and cache.
    - On Windows: %LOCALAPPDATA%/ReadAloud or GLib.get_user_data_dir()
    - On Linux: ~/.local/share/ReadAloud or GLib.get_user_data_dir()
    """
    if sys.platform != "win32" and HAS_GLIB:
        try:
            return Path(GLib.get_user_data_dir())
        except Exception:
            pass

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "ReadAloud"
        return Path.home() / "AppData" / "Local" / "ReadAloud"

    # Default POSIX fallback
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / "ReadAloud"
    return Path.home() / ".local" / "share" / "ReadAloud"


def get_model_search_paths() -> list[Path]:
    """
    Returns ordered list of candidate search directories for Piper ONNX voice models.
    Supports Windows portable layout (models/ next to .exe), Windows user data,
    PyInstaller bundled models, Linux Flatpak paths, and user home directories.
    """
    paths = []
    seen = set()

    def add_path(p: Path | None):
        if p is None:
            return
        p_resolved = p.resolve() if p.exists() else p
        p_str = str(p_resolved)
        if p_str not in seen:
            seen.add(p_str)
            paths.append(p_resolved)

    # 1. Models folder directly next to the executable (Windows portable / onedir mode)
    add_path(get_executable_dir() / "models")

    # 2. Bundled models inside PyInstaller internal directory
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        add_path(Path(sys._MEIPASS) / "models")

    # 3. User data directory models (e.g. %LOCALAPPDATA%/models or %LOCALAPPDATA%/ReadAloud/models)
    user_data = get_user_data_dir()
    add_path(user_data / "models")
    if user_data.name != "ReadAloud":
        add_path(user_data / "ReadAloud" / "models")

    # 4. Source tree models (development mode)
    repo_root = Path(__file__).resolve().parent.parent
    add_path(repo_root / "models")

    # 5. User home directory models (~/readaloud/models)
    add_path(Path.home() / "readaloud" / "models")

    # 6. Linux / Debian / Flatpak system directories (safe no-op on Windows)
    if sys.platform != "win32":
        add_path(Path("/usr/share/readaloud/models"))
        add_path(Path("/usr/local/share/readaloud/models"))
        add_path(Path("/app/share/readaloud/models"))
        add_path(Path.home() / ".var" / "app" / "im.zackarious.ReadAloud" / "data" / "models")

    return paths


def get_resource_bundle_path() -> Path | None:
    """
    Locates the compiled readaloud.gresource bundle.
    """
    candidates = [
        # Inside PyInstaller bundle
        get_app_dir() / "readaloud.gresource",
        get_executable_dir() / "readaloud.gresource",
        get_app_dir() / "src" / "readaloud.gresource",
        get_executable_dir() / "_internal" / "readaloud.gresource",
        # Source tree build directories
        Path(__file__).resolve().parent.parent / "build" / "src" / "readaloud.gresource",
        Path(__file__).resolve().parent.parent / "build-dir" / "readaloud.gresource",
        Path(__file__).resolve().parent.parent / "src" / "readaloud.gresource",
        # Flatpak / system install paths
        Path("/app/share/readaloud/readaloud.gresource"),
        Path("/usr/share/readaloud/readaloud.gresource"),
        Path("/usr/local/share/readaloud/readaloud.gresource"),
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def get_espeak_data_dir() -> Path | None:
    """
    Locates the espeak-ng-data phoneme table directory required by Piper phonemization.
    Prevents silent native C exit(1) when loading Piper models.
    """
    # 1. Environment variable override
    for env_var in ("ESPEAK_DATA_PATH", "ESPEAK_DATA_DIR"):
        env_val = os.environ.get(env_var)
        if env_val:
            p = Path(env_val)
            if p.is_dir() and (p / "phontab").is_file():
                return p
            # In case env_val points to parent directory containing espeak-ng-data
            if (p / "espeak-ng-data" / "phontab").is_file():
                return p / "espeak-ng-data"

    candidates = []

    if is_frozen():
        candidates.extend([
            get_app_dir() / "piper" / "espeak-ng-data",
            get_app_dir() / "_internal" / "piper" / "espeak-ng-data",
            get_executable_dir() / "_internal" / "piper" / "espeak-ng-data",
            get_executable_dir() / "piper" / "espeak-ng-data",
            get_app_dir() / "espeak-ng-data",
            get_app_dir() / "_internal" / "espeak-ng-data",
            get_executable_dir() / "espeak-ng-data",
            get_executable_dir() / "_internal" / "espeak-ng-data",
        ])

    # Development mode: inspect piper package location
    try:
        import piper
        piper_pkg_dir = Path(piper.__file__).resolve().parent
        candidates.extend([
            piper_pkg_dir / "espeak-ng-data",
            piper_pkg_dir.parent / "piper" / "espeak-ng-data",
            piper_pkg_dir.parent / "espeak-ng-data",
        ])
    except Exception:
        pass

    # Standard system or local directories
    candidates.extend([
        Path.home() / ".local" / "share" / "espeak-ng-data",
        Path("/usr/share/espeak-ng-data"),
        Path("/usr/lib/x86_64-linux-gnu/espeak-ng-data"),
        Path("/usr/lib/espeak-ng-data"),
        Path("/app/share/espeak-ng-data"),
    ])

    seen = set()
    for c in candidates:
        c_str = str(c)
        if c_str in seen:
            continue
        seen.add(c_str)
        if c.is_dir() and (c / "phontab").is_file():
            return c

    return None

