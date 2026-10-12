"""Restart only a verified local MIST listener for this repair's tests."""
import argparse
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--production', action='store_true')
a = p.parse_args()
port = 8790 if a.production else 8791
root = Path(__file__).resolve().parents[2]
result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, check=True)
for line in result.stdout.splitlines():
    fields = line.split()
    if len(fields) == 5 and fields[1] == f'127.0.0.1:{port}' and fields[3] == 'LISTENING':
        import psutil
        process = psutil.Process(int(fields[4]))
        command = process.cmdline()
        assert any('duplex/server.py' in arg.replace('\\', '/') for arg in command), command
        process.terminate()
        process.wait(10)
folder = root / 'brain/results/voice_quality_20260914'
folder.mkdir(exist_ok=True)
name = 'production' if a.production else 'staging'
args = ['python', 'brain/duplex/server.py', '--port', str(port), '--pair-code',
        'Opn9i4-QlEOTRJHN' if a.production else 'quality-local-test', '--run-dir',
        'brain/results/duplex-current' if a.production else 'brain/results/voice_quality_20260914/runtime']
if not a.production:
    args.append('--enable-fixtures')
with (folder / f'{name}.stdout.log').open('w') as stdout, (folder / f'{name}.stderr.log').open('w') as stderr:
    process = subprocess.Popen(args, cwd=root, stdout=stdout, stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW)
print(name, process.pid)
