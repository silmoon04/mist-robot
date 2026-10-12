"""Load this R5 Fusion runtime by absolute path, independently of cached R4 modules."""

import hashlib
import importlib.util
from pathlib import Path
import sys


def load_runtime():
    folder = Path(__file__).resolve().parent
    source = folder / "fusion_import.py"
    payload = source.read_bytes()
    path_digest = hashlib.sha256(str(source).casefold().encode()).hexdigest()[:12]
    name = "hex_quad_r5_fusion_runtime_" + path_digest
    specification = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    exec(compile(payload, str(source), "exec"), module.__dict__)
    if module.GROUP != "hexapod_phone_quad_r5_20260912" or module.HERE != folder:
        raise RuntimeError("R5 Fusion runtime namespace or source directory mismatch")
    if module.OUTPUT != folder / "output" or module.DESTINATION != folder / "output/fusion":
        raise RuntimeError("R5 Fusion output directory is not isolated")
    module.RUNTIME_SOURCE_SHA256 = hashlib.sha256(payload).hexdigest()
    module.RUNTIME_NAMESPACE = name
    return module
