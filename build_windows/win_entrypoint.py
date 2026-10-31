# win_entrypoint.py
#
# Copyright 2025-2026 Walter Bernard / zackarious
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
from pathlib import Path

_dll_directory_handles: list = []


def get_short_path_name(path_obj: Path | str) -> str:
    """Returns the Windows 8.3 short path name to avoid spaces or non-ASCII in native C fopen."""
    p_str = str(path_obj)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
            _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            _GetShortPathNameW.restype = wintypes.DWORD
            buf = ctypes.create_unicode_buffer(1024)
            ret = _GetShortPathNameW(p_str, buf, 1024)
            if ret > 0:
                return buf.value
        except Exception:
            pass
    return p_str


if sys.platform == "win32":
    # Redirect stdout and stderr to persistent log file when frozen without console
    if getattr(sys, "frozen", False):
        try:
            local_app = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
            log_dir = Path(local_app) / "ReadAloud"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = open(log_dir / "readaloud.log", "a", encoding="utf-8", buffering=1)
            sys.stdout = log_file
            sys.stderr = log_file
            print("\n--- ReadAloud Windows Session Started ---")
        except Exception:
            pass

    # Ensure Windows loader can locate bundled DLLs (python3.dll, onnxruntime.dll, etc.)
    dll_candidates = [Path(sys.executable).resolve().parent]
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()
        dll_candidates.extend([
            base_dir,
            base_dir / "_internal",
            base_dir / "_internal" / "onnxruntime" / "capi",
            base_dir / "onnxruntime" / "capi",
            base_dir / "piper",
            base_dir / "_internal" / "piper",
        ])
    for d in dll_candidates:
        if d.is_dir():
            d_str = str(d)
            if hasattr(os, "add_dll_directory"):
                try:
                    _dll_directory_handles.append(os.add_dll_directory(d_str))
                except Exception:
                    pass
            try:
                import ctypes
                ctypes.windll.kernel32.SetDllDirectoryW(d_str)
            except Exception:
                pass


def find_and_setup_espeak_data() -> str | None:
    """Finds espeak-ng-data directory and sets up ESPEAK_DATA_PATH with short 8.3 path."""
    candidates = []
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([
            base_dir / "piper" / "espeak-ng-data",
            base_dir / "_internal" / "piper" / "espeak-ng-data",
            base_dir / "espeak-ng-data",
            base_dir / "_internal" / "espeak-ng-data",
            exe_dir / "piper" / "espeak-ng-data",
            exe_dir / "_internal" / "piper" / "espeak-ng-data",
            exe_dir / "espeak-ng-data",
            exe_dir / "_internal" / "espeak-ng-data",
        ])

    try:
        import piper
        pkg_dir = Path(piper.__file__).resolve().parent
        candidates.extend([
            pkg_dir / "espeak-ng-data",
            pkg_dir.parent / "piper" / "espeak-ng-data",
            pkg_dir.parent / "espeak-ng-data",
        ])
    except Exception:
        pass

    found = None
    for cand in candidates:
        if cand.is_dir() and (cand / "phontab").is_file():
            found = cand
            break

    if found:
        short_path = get_short_path_name(found)
        os.environ["ESPEAK_DATA_PATH"] = short_path
        os.environ["ESPEAK_DATA_DIR"] = short_path
        print(f"[win_entrypoint] Configured ESPEAK_DATA_PATH={short_path}")
        return short_path
    return None


# Discover espeak-ng-data and set environment variable before loading C extensions
_espeak_data_path = find_and_setup_espeak_data()

# CRITICAL: Pre-initialize MSVC C-extensions before MinGW64 GLib/GTK runtime DLLs
# are added to the loader search path to prevent CRT/TLS conflicts.
try:
    import numpy
    import onnxruntime
    import piper
    import sounddevice
    import lameenc
except Exception as e:
    print(f"[win_entrypoint] Pre-init notice: {e}")

def setup_windows_environment():
    """Sets up runtime environment variables for GTK4, Libadwaita, and GStreamer."""
    if sys.platform != "win32":
        return

    # Enable Per-Monitor DPI Awareness v2 for crisp rendering on high-DPI displays
    try:
        import ctypes
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            # Fallback: PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    # When running as a frozen PyInstaller bundle
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()
        if not base_dir.is_dir():
            base_dir = Path(sys.executable).resolve().parent

        # Add base_dir and DLL directories to Windows PATH
        os.environ["PATH"] = f"{str(base_dir)};{str(base_dir / 'bin')};{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(base_dir))
                bin_dir = base_dir / "bin"
                if bin_dir.is_dir():
                    os.add_dll_directory(str(bin_dir))
            except Exception:
                pass

        # Schemas
        schema_dir = base_dir / "share" / "glib-2.0" / "schemas"
        if schema_dir.is_dir():
            os.environ["GSETTINGS_SCHEMA_DIR"] = str(schema_dir)

        # Typelibs
        typelib_dir = base_dir / "lib" / "girepository-1.0"
        if typelib_dir.is_dir():
            os.environ["GI_TYPELIB_PATH"] = str(typelib_dir)

        # GdkPixbuf loaders
        pixbuf_cache = base_dir / "lib" / "gdk-pixbuf-2.0" / "2.10.0" / "loaders.cache"
        if pixbuf_cache.is_file():
            os.environ["GDK_PIXBUF_MODULE_FILE"] = str(pixbuf_cache)

        # GStreamer plugins
        gst_plugin_dir = base_dir / "lib" / "gstreamer-1.0"
        if gst_plugin_dir.is_dir():
            os.environ["GST_PLUGIN_SYSTEM_PATH_1_0"] = str(gst_plugin_dir)
            os.environ["GST_PLUGIN_PATH_1_0"] = str(gst_plugin_dir)

        # GStreamer scanner
        gst_scanner = base_dir / "libexec" / "gstreamer-1.0" / "gst-plugin-scanner.exe"
        if gst_scanner.is_file():
            os.environ["GST_PLUGIN_SCANNER_1_0"] = str(gst_scanner)

        # Force Libadwaita theme
        if "GTK_THEME" not in os.environ:
            os.environ["GTK_THEME"] = "Adwaita"

def main():
    setup_windows_environment()

    # Add repository root / bundle root to sys.path
    app_root = Path(__file__).resolve().parent.parent
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))

    # Initialize PyGObject requirements
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')

    # Load resources
    from src.paths import get_resource_bundle_path
    bundle_path = get_resource_bundle_path()
    if bundle_path and bundle_path.is_file():
        from gi.repository import Gio
        try:
            res = Gio.Resource.load(str(bundle_path))
            res._register()
        except Exception as e:
            print(f"Notice: Gio.Resource.load info: {e}")

    # Launch application
    from src.main import main as app_main
    sys.exit(app_main("1.8.10"))

if __name__ == "__main__":
    main()
