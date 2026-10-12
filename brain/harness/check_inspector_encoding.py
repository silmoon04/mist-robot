from pathlib import Path
import re
for p in (Path(__file__).resolve().parents[1]/'duplex/static').glob('*.js'):
    if p.name not in ('debug.js','expressions.js'):continue
    s=p.read_text(encoding='utf-8')
    print(p.name,sorted({m.group().encode('unicode_escape').decode() for m in re.finditer(r'[^\x00-\x7f]+',s)}))
