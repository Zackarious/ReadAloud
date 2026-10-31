"""Lightweight, 100% stable ctypes-based ONNX Runtime inference engine.

Provides full compatibility for Piper neural speech synthesis without
requiring MSVC C-extension compilation or pybind11 ABI bindings.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

import ctypes.util

# Discover onnxruntime shared library
_lib = None
_candidates: list[str | Path] = []

if sys.platform == "win32":
    if getattr(sys, "frozen", False):
        exe_dir = Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()
        _candidates.extend([
            exe_dir / "onnxruntime.dll",
            exe_dir / "_internal" / "onnxruntime.dll",
            exe_dir / "_internal" / "onnxruntime" / "capi" / "onnxruntime.dll",
            Path(sys.executable).resolve().parent / "onnxruntime.dll",
        ])
    prefix = os.environ.get("MINGW_PREFIX", r"C:\msys64\ucrt64")
    _candidates.extend([
        Path(prefix) / "bin" / "onnxruntime.dll",
        Path(sys.executable).parent / "onnxruntime.dll",
        Path(r"C:\msys64\ucrt64\bin\onnxruntime.dll"),
        Path(r"C:\msys64\mingw64\bin\onnxruntime.dll"),
        "onnxruntime.dll",
    ])
else:
    found = ctypes.util.find_library("onnxruntime")
    if found:
        _candidates.append(found)
    _candidates.extend([
        Path(__file__).parent / "capi" / "libonnxruntime.so",
        Path(__file__).parent / "libonnxruntime.so",
        "libonnxruntime.so",
        "libonnxruntime.so.1",
        "/usr/lib/libonnxruntime.so",
    ])
    # Search site-packages
    for p in sys.path:
        for f in Path(p).glob("**/libonnxruntime.so*"):
            _candidates.append(f)

_errors: list[str] = []

if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    bin_dir = Path(sys.executable).parent.resolve()
    if bin_dir.is_dir():
        try:
            os.add_dll_directory(str(bin_dir))
        except Exception:
            pass

for cand in _candidates:
    try:
        p_cand = Path(cand)
        if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
            cand_dir = p_cand.parent.resolve() if p_cand.is_file() else None
            if cand_dir and cand_dir.is_dir():
                try:
                    os.add_dll_directory(str(cand_dir))
                except Exception:
                    pass
        _lib = ctypes.CDLL(str(cand))
        break
    except Exception as err:
        _errors.append(f"{cand}: {err}")
        continue

if not _lib:
    found = ctypes.util.find_library("onnxruntime")
    if found:
        try:
            _lib = ctypes.CDLL(found)
        except Exception as err:
            _errors.append(f"{found}: {err}")

if not _lib:
    details = "\n  ".join(_errors)
    raise ImportError(f"Could not load onnxruntime shared library. Errors encountered:\n  {details}")


class _OrtApiBase(ctypes.Structure):
    _fields_ = [
        ("GetApi", ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_uint32)),
        ("GetVersionString", ctypes.CFUNCTYPE(ctypes.c_char_p)),
    ]


_lib.OrtGetApiBase.restype = ctypes.POINTER(_OrtApiBase)
_base = _lib.OrtGetApiBase().contents

_api_ptr = None
for _v in (18, 17, 16, 15, 14, 13, 12, 11, 10, 8, 7, 6, 5, 4, 3, 2, 1):
    _api_ptr = _base.GetApi(_v)
    if _api_ptr:
        break

if not _api_ptr:
    raise RuntimeError("Could not obtain OrtApi function table from onnxruntime library")

_funcs = (ctypes.c_void_p * 270).from_address(_api_ptr)

# C-API function bindings
_CreateEnv = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)
)(_funcs[3])
_CreateSessionOptions = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
)(_funcs[10])
_CreateSessionFromArray = ctypes.CFUNCTYPE(
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_void_p),
)(_funcs[8])
_Run = ctypes.CFUNCTYPE(
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_char_p),
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_char_p),
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_void_p),
)(_funcs[9])
_SessionGetInputCount = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)
)(_funcs[30])
_SessionGetOutputCount = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)
)(_funcs[31])
_GetAllocatorWithDefaultOptions = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
)(_funcs[78])
_SessionGetInputName = ctypes.CFUNCTYPE(
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_char_p),
)(_funcs[36])
_SessionGetOutputName = ctypes.CFUNCTYPE(
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_char_p),
)(_funcs[37])
_CreateCpuMemoryInfo = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
)(_funcs[69])
_CreateTensorWithDataAsOrtValue = ctypes.CFUNCTYPE(
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_int64),
    ctypes.c_size_t,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_void_p),
)(_funcs[49])
_GetTensorTypeAndShape = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
)(_funcs[65])
_GetDimensionsCount = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)
)(_funcs[61])
_GetDimensions = ctypes.CFUNCTYPE(
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_int64),
    ctypes.c_size_t,
)(_funcs[62])
_GetTensorElementType = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)
)(_funcs[60])
_GetTensorMutableData = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
)(_funcs[51])
_ReleaseValue = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(_funcs[96])
_ReleaseSession = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(_funcs[95])

# Process-wide environment and CPU memory configuration
_g_env = ctypes.c_void_p()
_CreateEnv(3, b"piper", ctypes.byref(_g_env))
_g_mem = ctypes.c_void_p()
_CreateCpuMemoryInfo(0, 0, ctypes.byref(_g_mem))


class SessionOptions:
    execution_mode: int = 0
    graph_optimization_level: int = 99


class GraphOptimizationLevel:
    ORT_ENABLE_ALL: int = 99


class ExecutionMode:
    ORT_SEQUENTIAL: int = 0


class _NodeArg:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"NodeArg(name='{self.name}')"


class InferenceSession:
    def __init__(
        self,
        path_or_bytes: str | Path | bytes | bytearray,
        sess_options: Any = None,
        providers: list[str] | None = None,
    ):
        if isinstance(path_or_bytes, (str, Path)):
            self._raw = Path(path_or_bytes).read_bytes()
        else:
            self._raw = bytes(path_or_bytes)

        opts = ctypes.c_void_p()
        _CreateSessionOptions(ctypes.byref(opts))

        self._session = ctypes.c_void_p()
        st = _CreateSessionFromArray(
            _g_env, self._raw, len(self._raw), opts, ctypes.byref(self._session)
        )
        if st or not self._session:
            raise RuntimeError(f"Failed to create ONNX session: {st}")

        alloc = ctypes.c_void_p()
        _GetAllocatorWithDefaultOptions(ctypes.byref(alloc))

        n_in = ctypes.c_size_t()
        _SessionGetInputCount(self._session, ctypes.byref(n_in))
        self._inputs: list[_NodeArg] = []
        for i in range(n_in.value):
            name_p = ctypes.c_char_p()
            _SessionGetInputName(self._session, i, alloc, ctypes.byref(name_p))
            if name_p.value:
                self._inputs.append(_NodeArg(name_p.value.decode("utf-8")))

        n_out = ctypes.c_size_t()
        _SessionGetOutputCount(self._session, ctypes.byref(n_out))
        self._outputs: list[_NodeArg] = []
        for i in range(n_out.value):
            name_p = ctypes.c_char_p()
            _SessionGetOutputName(self._session, i, alloc, ctypes.byref(name_p))
            if name_p.value:
                self._outputs.append(_NodeArg(name_p.value.decode("utf-8")))

    def get_inputs(self) -> list[_NodeArg]:
        return self._inputs

    def get_outputs(self) -> list[_NodeArg]:
        return self._outputs

    def run(
        self,
        output_names: list[str] | None,
        input_feed: dict[str, Any],
    ) -> list[np.ndarray | None]:
        in_names: list[bytes] = []
        in_vals: list[ctypes.c_void_p] = []
        keep_alive: list[np.ndarray] = []

        for name, val in input_feed.items():
            if not isinstance(val, np.ndarray):
                val = np.array(val)
            val = np.ascontiguousarray(val)
            keep_alive.append(val)

            # Map numpy dtype to ONNX element type
            if val.dtype == np.float32:
                elem_type = 1
            elif val.dtype == np.int64:
                elem_type = 7
            elif val.dtype == np.int32:
                elem_type = 6
            elif val.dtype == bool:
                elem_type = 9
            else:
                elem_type = 1

            v = ctypes.c_void_p()
            shape_arr = (ctypes.c_int64 * len(val.shape))(*val.shape)
            st = _CreateTensorWithDataAsOrtValue(
                _g_mem,
                val.ctypes.data,
                val.nbytes,
                shape_arr,
                len(val.shape),
                elem_type,
                ctypes.byref(v),
            )
            if st or not v:
                raise RuntimeError(f"Failed to create input tensor for '{name}'")

            in_names.append(name.encode("utf-8"))
            in_vals.append(v)

        if not output_names:
            out_names_list = [o.name.encode("utf-8") for o in self._outputs]
        else:
            out_names_list = [
                o.encode("utf-8") if isinstance(o, str) else o for o in output_names
            ]

        n_in = len(in_names)
        n_out = len(out_names_list)

        c_in_n = (ctypes.c_char_p * n_in)(*in_names)
        c_in_v = (ctypes.c_void_p * n_in)(*in_vals)
        c_out_n = (ctypes.c_char_p * n_out)(*out_names_list)
        c_out_v = (ctypes.c_void_p * n_out)(*[ctypes.c_void_p() for _ in range(n_out)])

        st = _Run(
            self._session,
            None,
            c_in_n,
            c_in_v,
            n_in,
            c_out_n,
            n_out,
            c_out_v,
        )

        for v in in_vals:
            if v:
                _ReleaseValue(v)

        if st:
            raise RuntimeError(f"InferenceSession.run failed with status: {st}")

        results: list[np.ndarray | None] = []
        for i in range(n_out):
            out_v = c_out_v[i]
            if not out_v:
                results.append(None)
                continue

            info = ctypes.c_void_p()
            _GetTensorTypeAndShape(out_v, ctypes.byref(info))

            dim_count = ctypes.c_size_t()
            _GetDimensionsCount(info, ctypes.byref(dim_count))
            dims = (ctypes.c_int64 * dim_count.value)()
            _GetDimensions(info, dims, dim_count.value)
            out_shape = list(dims)

            elem_type = ctypes.c_int()
            _GetTensorElementType(info, ctypes.byref(elem_type))

            if elem_type.value == 7:
                ctype: Any = ctypes.c_int64
            elif elem_type.value == 6:
                ctype = ctypes.c_int32
            else:
                ctype = ctypes.c_float

            data_ptr = ctypes.c_void_p()
            _GetTensorMutableData(out_v, ctypes.byref(data_ptr))

            res_arr = np.ctypeslib.as_array(
                ctypes.cast(data_ptr, ctypes.POINTER(ctype)), shape=out_shape
            ).copy()

            _ReleaseValue(out_v)
            results.append(res_arr)

        return results
