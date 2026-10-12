"""Refresh native measurements and exports after an already verified joint build."""
from pathlib import Path
import sys
import importlib


def run(_context: str):
    folder=str(Path(__file__).resolve().parent)
    if folder not in sys.path:
        sys.path.insert(0,folder)
    import fusion_import
    fusion_import=importlib.reload(fusion_import)
    fusion_import.run('inspect')
    return fusion_import.run('export')
