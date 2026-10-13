"""Measure live simulation pacing and command clipping, with a final zero command."""
import argparse
import json
import time
from urllib.request import Request, urlopen

p = argparse.ArgumentParser()
p.add_argument('--url', default='http://127.0.0.1:8131')
p.add_argument('--requested-vx', type=float, default=.04)
p.add_argument('--output', required=True)
a = p.parse_args()
def request(path, data=None):
    req = Request(a.url + path, data=None if data is None else json.dumps(data).encode(),
                  headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=10) as response:
        return json.load(response)

first = request('/api/state')
start = time.monotonic()
time.sleep(2)
second = request('/api/state')
end = time.monotonic()
result = {'initial_controller': first['controller'], 'initial_payload_kg': first['info']['phone_mass_kg'],
          'wall_elapsed_s': end-start, 'simulation_elapsed_s': second['info']['time_s']-first['info']['time_s']}
try:
    request('/api/command', {'command': [a.requested_vx, 0, 0]})
    deadline = time.monotonic()+.3
    state = request('/api/state')
    while abs(state['info']['command'][0])<1e-8 and time.monotonic()<deadline:
        time.sleep(.02)
        state = request('/api/state')
    result.update(requested_vx=a.requested_vx, accepted_command=state['info']['command'])
finally:
    request('/api/command', {'command': [0, 0, 0]})
result['real_time_factor'] = result['simulation_elapsed_s']/result['wall_elapsed_s']
result['command_matches_request'] = abs(result['accepted_command'][0]-a.requested_vx)<1e-6
from pathlib import Path
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
Path(a.output).write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
assert result['command_matches_request'], 'Remote silently clips requested walking speed'
