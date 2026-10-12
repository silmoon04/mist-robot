from pathlib import Path
root=Path(__file__).resolve().parents[1]
for name in ('debug.js','expressions.js','inspect.css'):
    p=root/'duplex/static'/name;s=p.read_text(encoding='utf-8')
    s=s.replace('\u00c3\u201a\u00b7','·')
    # Resolve the longer forms before their suffixes on a second pass.
    for character in ('·','→','×'):
        variants=[];bad=character
        for _ in range(3):
            try:bad=bad.encode('utf-8').decode('cp1252');variants.append(bad)
            except UnicodeError:break
        for bad in reversed(variants):s=s.replace(bad,character)
    p.write_text(s,encoding='utf-8')
for name in ('refine_debug_ui.py','final_debug_ui.py'):
    p=root/'harness'/name;s=p.read_text(encoding='utf-8').replace('.read_text()',".read_text(encoding='utf-8')");p.write_text(s,encoding='utf-8')
