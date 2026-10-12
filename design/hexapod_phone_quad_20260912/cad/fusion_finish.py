"""Complete joints, measurements and exports for the imported quadruped."""
from pathlib import Path
import sys


def run(_context: str):
    folder=str(Path(__file__).resolve().parent)
    if folder not in sys.path:
        sys.path.insert(0,folder)
    import fusion_import
    import importlib
    fusion_import = importlib.reload(fusion_import)
    fusion_import.run('joints')
    fusion_import.run('inspect')
    return fusion_import.run('export')
