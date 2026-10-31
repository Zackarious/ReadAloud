"""Pure ctypes replacement for piper.espeakbridge using native libespeak-ng.

Bypasses MSVC CPython extension ABI incompatibilities by interfacing directly
with libespeak-ng C-API exports (espeak_Initialize, espeak_SetVoiceByName,
and espeak_TextToPhonemesWithTerminator).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path
from typing import List, Tuple

_lib = None
_lib_handle = None

# Clause terminators according to espeak-ng internal bitmasks
_TERMINATOR_MAP = {
    0x80028: ".",
    0x82028: "?",
    0x8302d: "!",
    0x41014: ",",
    0x4001e: ":",
    0x4101e: ";",
}


def _find_libespeak() -> str | None:
    """Locates libespeak-ng shared library across bundled and system paths."""
    candidates = []

    if sys.platform == "win32":
        if getattr(sys, "frozen", False):
            base_dir = Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()
            exe_dir = Path(sys.executable).resolve().parent
            candidates.extend([
                base_dir / "libespeak-ng.dll",
                base_dir / "_internal" / "libespeak-ng.dll",
                base_dir / "bin" / "libespeak-ng.dll",
                exe_dir / "libespeak-ng.dll",
                exe_dir / "_internal" / "libespeak-ng.dll",
            ])
        prefix = os.environ.get("MINGW_PREFIX") or os.environ.get("MSYSTEM_PREFIX")
        if prefix:
            candidates.append(Path(prefix) / "bin" / "libespeak-ng.dll")
        candidates.extend([
            Path(r"C:\msys64\ucrt64\bin\libespeak-ng.dll"),
            Path(r"C:\msys64\mingw64\bin\libespeak-ng.dll"),
            Path(sys.executable).parent / "libespeak-ng.dll",
            "libespeak-ng.dll",
        ])
    else:
        found = ctypes.util.find_library("espeak-ng")
        if found:
            candidates.append(found)
        candidates.extend([
            "libespeak-ng.so.1",
            "libespeak-ng.so",
            "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1",
            "/usr/lib/libespeak-ng.so.1",
            "/app/lib/libespeak-ng.so.1",
        ])

    for cand in candidates:
        if isinstance(cand, Path):
            if cand.is_file():
                return str(cand)
        elif isinstance(cand, str):
            try:
                ctypes.cdll.LoadLibrary(cand)
                return cand
            except Exception:
                pass
    return None


def _get_lib():
    global _lib, _lib_handle
    if _lib is not None:
        return _lib

    lib_path = _find_libespeak()
    if not lib_path:
        raise ImportError("Could not locate native libespeak-ng shared library.")

    if sys.platform == "win32":
        # Ensure DLL directory is added for any dependencies
        p = Path(lib_path).resolve().parent
        if p.is_dir() and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(p))
            except Exception:
                pass
        _lib_handle = ctypes.CDLL(str(lib_path), winmode=0)
    else:
        _lib_handle = ctypes.CDLL(str(lib_path))

    # Bind C signatures
    # int espeak_Initialize(espeak_AUDIO_OUTPUT output, int buflength, const char *path, int options)
    _lib_handle.espeak_Initialize.restype = ctypes.c_int
    _lib_handle.espeak_Initialize.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
    ]

    # espeak_ERROR espeak_SetVoiceByName(const char *name)
    _lib_handle.espeak_SetVoiceByName.restype = ctypes.c_int
    _lib_handle.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]

    # const char *espeak_TextToPhonemesWithTerminator(const void **textptr, int textmode, int phonememode, int *terminator)
    _lib_handle.espeak_TextToPhonemesWithTerminator.restype = ctypes.c_char_p
    _lib_handle.espeak_TextToPhonemesWithTerminator.argtypes = [
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
    ]

    _lib = _lib_handle
    return _lib


def initialize(path: str | None = None) -> None:
    """Initializes espeak-ng speech synthesis engine with data directory."""
    lib = _get_lib()
    path_bytes = str(path).encode("utf-8") if path else None
    # AUDIO_OUTPUT_SYNCHRONOUS = 2
    res = lib.espeak_Initialize(2, 0, path_bytes, 0)
    if res < 0:
        raise RuntimeError(f"espeak_Initialize failed with return code {res}")


def set_voice(voice: str) -> None:
    """Sets active phonemization voice."""
    lib = _get_lib()
    res = lib.espeak_SetVoiceByName(str(voice).encode("utf-8"))
    if res != 0:
        # Retry with lower-case or fallback
        lib.espeak_SetVoiceByName(str(voice).lower().encode("utf-8"))


def get_phonemes(text: str) -> List[Tuple[str, str, bool]]:
    """Converts input text to list of (phonemes_str, terminator_str, end_of_sentence) tuples."""
    lib = _get_lib()
    text_bytes = text.encode("utf-8")
    p = ctypes.c_char_p(text_bytes)
    p_ptr = ctypes.pointer(p)
    term = ctypes.c_int(0)
    clauses: List[Tuple[str, str, bool]] = []

    # Text mode 0 = espeakCHARS_AUTO, Phoneme mode 2 = espeakPHONEMES_IPA
    while p.value and len(p.value) > 0:
        res = lib.espeak_TextToPhonemesWithTerminator(p_ptr, 0, 2, ctypes.byref(term))
        val = term.value & 0xFFFFF
        term_str = _TERMINATOR_MAP.get(val, "")
        is_eos = bool(term.value & 0x80000)
        ph_str = res.decode("utf-8", errors="replace") if res else ""
        clauses.append((ph_str, term_str, is_eos))

    return clauses
