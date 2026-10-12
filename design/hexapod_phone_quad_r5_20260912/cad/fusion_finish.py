"""Complete joints, measurements and exports for the imported quadruped."""
from pathlib import Path
import importlib.util


def run(_context: str):
    source = Path(__file__).resolve().with_name('fusion_runtime_r5.py')
    spec = importlib.util.spec_from_file_location('hex_quad_r5_runtime_loader', source)
    loader = importlib.util.module_from_spec(spec)
    exec(compile(source.read_bytes(), str(source), 'exec'), loader.__dict__)
    fusion_import = loader.load_runtime()
    fusion_import.run('joints')
    fusion_import.run('inspect')
    return fusion_import.run('export')
