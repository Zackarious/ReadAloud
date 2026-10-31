# error_logger.py
#
# Copyright 2025-2026 Walter Bernard / zackarious
#
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import os
import platform
import sys
import tempfile
import threading
import traceback
from pathlib import Path


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
    version = "1.8.10"
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
    Installs global unhandled exception hooks for the main thread and background threads.
    """
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
