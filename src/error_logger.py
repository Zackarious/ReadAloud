# error_logger.py
#
# Copyright 2025-2026 Walter Bernard / zackarious
#
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import faulthandler
import json
import os
import platform
import signal
import sys
import tempfile
import threading
import traceback
from pathlib import Path

_faulthandler_file = None
_session_tracking_active = False


def get_error_log_path() -> Path:
    """
    Determines the path where error.log should be written.
    Prioritizes the application/executable directory (e.g. C:\\Users\\<user>\\AppData\\Local\\Programs\\ReadAloud),
    falling back to user data directory or temp directory if read-only.
    """
    candidates = []

    # 1. Executable directory (where ReadAloud.exe resides)
    try:
        from .paths import get_executable_dir
        exe_dir = get_executable_dir()
        candidates.append(exe_dir / "error.log")
    except Exception:
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().parent / "error.log")
        else:
            candidates.append(Path(__file__).resolve().parent.parent / "error.log")

    # 2. User AppData directory (e.g. %LOCALAPPDATA%/ReadAloud or ~/.local/share/ReadAloud)
    try:
        from .paths import get_user_data_dir
        user_dir = get_user_data_dir()
        candidates.append(user_dir / "error.log")
    except Exception:
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidates.append(Path(local_app) / "ReadAloud" / "error.log")

    # 3. System temp directory fallback
    try:
        candidates.append(Path(tempfile.gettempdir()) / "ReadAloud" / "error.log")
    except Exception:
        pass

    # Find first writable path
    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            with open(candidate, "a", encoding="utf-8") as f:
                pass
            return candidate.resolve()
        except Exception:
            continue

    return candidates[0] if candidates else Path("error.log").resolve()


def get_crash_marker_path() -> Path:
    """
    Returns the path where session_marker.json is stored.
    Stored in the writable user data directory.
    """
    try:
        from .paths import get_user_data_dir
        user_dir = get_user_data_dir()
        return user_dir / "session_marker.json"
    except Exception:
        return Path(tempfile.gettempdir()) / "ReadAloud" / "session_marker.json"


def start_session_tracking():
    """
    Records the startup of the current ReadAloud process into session_marker.json.
    clean_exit is initialized to False; if the process terminates abnormally,
    the next launch will detect this unclosed session.
    """
    global _session_tracking_active
    marker_path = get_crash_marker_path()
    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        version = "1.8.17"
        try:
            from . import __version__
            version = __version__
        except Exception:
            pass

        data = {
            "pid": os.getpid(),
            "version": version,
            "start_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "clean_exit": False,
            "state": "idle",
            "activity": {},
            "platform": f"{sys.platform} ({platform.platform()})",
            "python": sys.version.split()[0],
        }
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        _session_tracking_active = True
    except Exception as e:
        try:
            sys.stderr.write(f"Warning: Failed to start session tracking: {e}\n")
        except Exception:
            pass


def update_session_activity(state: str, **kwargs):
    """
    Updates the session marker with current activity breadcrumbs (e.g. state='synthesizing',
    voice='...', word_count=..., sentence_index=...).
    """
    marker_path = get_crash_marker_path()
    try:
        if not marker_path.is_file():
            return
        with open(marker_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["state"] = state
        data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "activity" not in data or not isinstance(data["activity"], dict):
            data["activity"] = {}
        data["activity"].update(kwargs)
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception:
        pass


def mark_clean_exit():
    """
    Marks the current session as having cleanly exited.
    """
    marker_path = get_crash_marker_path()
    try:
        if marker_path.is_file():
            with open(marker_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["clean_exit"] = True
            data["exit_time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with open(marker_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
    except Exception:
        pass


def check_previous_session_crash() -> dict | None:
    """
    Inspects session_marker.json on startup.
    If the previous session did not cleanly exit, records an abnormal termination
    entry in error.log, marks the marker as handled, and returns crash diagnostic metadata.
    Returns None if the previous session exited cleanly or no marker exists.
    """
    marker_path = get_crash_marker_path()
    try:
        if not marker_path.is_file():
            return None
        with open(marker_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # If previous exit was clean, no crash
        if data.get("clean_exit", True):
            return None

        # If PID is current PID (e.g. same session calling again), ignore
        if data.get("pid") == os.getpid():
            return None

        # Abnormal termination detected!
        prev_pid = data.get("pid", "Unknown")
        prev_start = data.get("start_time", "Unknown")
        prev_state = data.get("state", "Unknown")
        prev_activity = data.get("activity", {})
        prev_version = data.get("version", "Unknown")

        # Construct diagnostic summary
        summary_lines = [
            f"Unexpected application termination detected from previous session (PID {prev_pid}).",
            f"Started at: {prev_start}",
            f"State: {prev_state}",
        ]
        if prev_activity:
            for k, v in prev_activity.items():
                summary_lines.append(f"  {k}: {v}")

        diag_text = "\n".join(summary_lines)

        # Log into error.log
        log_path = log_error(
            "Abnormal Application Termination / Crash Detected",
            context="Crash Recovery / Previous Session Heartbeat",
            traceback_text=diag_text,
        )

        # Mark previous session as handled so we don't prompt repeatedly
        data["clean_exit"] = True
        data["crash_logged"] = True
        try:
            with open(marker_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

        return {
            "pid": prev_pid,
            "start_time": prev_start,
            "state": prev_state,
            "activity": prev_activity,
            "version": prev_version,
            "log_path": str(log_path),
            "log_excerpt": get_error_log_content(max_bytes=10000),
            "diagnostic_summary": diag_text,
        }
    except Exception as e:
        try:
            sys.stderr.write(f"Warning: Failed to check crash marker: {e}\n")
        except Exception:
            pass
        return None


def get_error_log_content(max_bytes: int = 100000) -> str:
    """
    Reads the error log file, returning up to max_bytes (most recent lines if truncated).
    """
    log_path = get_error_log_path()
    try:
        if not log_path.is_file():
            return "No error log file found."
        size = log_path.stat().st_size
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
                content = f.read()
                nl = content.find("\n")
                if nl != -1:
                    content = content[nl + 1:]
                return f"[... earlier entries truncated ({size} bytes total) ...]\n\n" + content
            return f.read()
    except Exception as e:
        return f"Unable to read error log: {e}"


def clear_error_log() -> bool:
    """
    Clears the contents of the error log file.
    """
    log_path = get_error_log_path()
    try:
        if log_path.is_file():
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("")
        return True
    except Exception:
        return False


def log_error(
    message: str,
    exc: BaseException | None = None,
    traceback_text: str | None = None,
    context: str | None = None,
) -> Path:
    """
    Logs a detailed diagnostic entry into error.log.
    Returns the absolute Path to the error.log file.
    """
    log_path = get_error_log_path()

    now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # App version
    version = "1.8.17"
    try:
        from . import __version__
        version = __version__
    except Exception:
        pass

    frozen_status = "Frozen (PyInstaller)" if getattr(sys, "frozen", False) else "Source / Unfrozen"

    # Gather traceback if not provided
    if not traceback_text and exc is not None:
        traceback_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    elif not traceback_text and sys.exc_info()[0] is not None:
        traceback_text = traceback.format_exc()

    entry_lines = [
        "================================================================================",
        f"ReadAloud Error Log - {now_local} ({now_utc})",
        "================================================================================",
        f"Version:      {version}",
        f"Execution:    {frozen_status}",
        f"Platform:     {sys.platform} ({platform.platform()})",
        f"Python:       {sys.version.split()[0]} ({platform.python_implementation()})",
        f"Executable:   {sys.executable}",
        f"Process ID:   {os.getpid()}",
    ]

    if context:
        entry_lines.append(f"Context:      {context}")

    entry_lines.append(f"Summary:      {message}")

    # Environment diagnostics
    env_keys = ["ESPEAK_DATA_PATH", "ESPEAK_DATA_DIR", "PATH"]
    env_info = []
    for k in env_keys:
        val = os.environ.get(k)
        if val:
            env_info.append(f"  {k} = {val}")
    if env_info:
        entry_lines.append("Environment:")
        entry_lines.extend(env_info)

    if traceback_text:
        entry_lines.append("Traceback (most recent call last):")
        entry_lines.append(traceback_text.rstrip())
    else:
        entry_lines.append("Traceback: Not available")

    entry_lines.append("================================================================================\n")

    full_entry = "\n".join(entry_lines)

    # Write to error.log
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(full_entry)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception as log_write_err:
        try:
            sys.stderr.write(f"Failed to write to {log_path}: {log_write_err}\n")
        except Exception:
            pass

    # Also emit to stderr
    try:
        sys.stderr.write(full_entry)
        sys.stderr.flush()
    except Exception:
        pass

    return log_path


def install_exception_hooks():
    """
    Installs global unhandled exception hooks for the main thread and background threads,
    enables Python faulthandler to write C-level crash dumps (SIGSEGV, SIGABRT, SIGBUS, SIGILL, SIGFPE)
    to error.log, and sets a clean exit handler.
    """
    global _faulthandler_file

    # 1. Enable faulthandler to catch native crashes (C++ segfaults, asserts in espeak-ng/piper)
    try:
        log_path = get_error_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Keep open in append mode for faulthandler
        _faulthandler_file = open(log_path, "a", encoding="utf-8")
        faulthandler.enable(file=_faulthandler_file, all_threads=True)
    except Exception as fh_err:
        try:
            sys.stderr.write(f"Warning: Could not enable faulthandler: {fh_err}\n")
        except Exception:
            pass

    # 2. Main thread unhandled exception hook
    orig_excepthook = sys.excepthook

    def custom_excepthook(exc_type, exc_value, exc_tb):
        try:
            tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            log_error(str(exc_value), exc=exc_value, traceback_text=tb_str, context="Unhandled Main Thread Exception")
        except Exception:
            pass
        if orig_excepthook:
            orig_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = custom_excepthook

    # 3. Background thread unhandled exception hook
    if hasattr(threading, "excepthook"):
        orig_thread_hook = threading.excepthook

        def custom_thread_excepthook(args):
            try:
                tb_str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
                thread_name = args.thread.name if args.thread else "UnknownThread"
                log_error(str(args.exc_value), exc=args.exc_value, traceback_text=tb_str, context=f"Unhandled Thread Exception ({thread_name})")
            except Exception:
                pass
            if orig_thread_hook:
                orig_thread_hook(args)

        threading.excepthook = custom_thread_excepthook

    # 4. Native signal handlers where appropriate (SIGTERM)
    def _sigterm_handler(signum, frame):
        try:
            log_error(f"Process received signal {signum} (SIGTERM/kill)", context="Signal Handler")
        except Exception:
            pass
        sys.exit(128 + signum)

    try:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    except Exception:
        pass
