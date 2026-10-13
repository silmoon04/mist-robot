"""Own the pose-streamed simulation and dry-run bridge through the supervisor."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from locomotion.scripts import remote_session as session


def process_identity(pid):
    try:
        proc = Path('/proc') / str(int(pid))
        fields = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()
        command = (proc / 'cmdline').read_bytes().split(b'\0')
        if str(Path(__file__).resolve()).encode() not in command or b'run' not in command:
            return None
        return fields[19]
    except (OSError, ValueError, TypeError, IndexError):
        return None


base_health = session.health


def health(name):
    if name != 'simulation':
        return base_health(name)
    import json
    from urllib.request import urlopen
    value = {'ready': False, 'url': 'http://127.0.0.1:8131/', 'error': None}
    try:
        with urlopen('http://127.0.0.1:8131/api/state', timeout=1) as response:
            state = json.load(response)
        accepted = (isinstance(state, dict) and {'controller', 'info', 'sensor', 'pose'} <= state.keys()
                    and state.get('interactive', {}).get('version') == 2
                    and state['pose'].get('version') == 1
                    and isinstance(state['pose'].get('links'), list))
        value.update(ready=accepted, mode='simulation', error=None if accepted else
                     'An earlier or incompatible simulator owns port 8131. Stop its session before starting the smooth remote.')
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        value.update(error=str(exc))
    return value


def configure_session():
    session.process_identity = process_identity
    session.health = health
    session.SERVICES = dict(session.SERVICES)
    session.SERVICES['simulation'] = (8131, '/api/state', [str(session.REPO / 'locomotion/sim_remote_interactive_v2.py'), '--port', '8131'])
    return session


if __name__ == '__main__':
    try:
        configure_session().main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f'MIST remote: {error}', file=sys.stderr)
        raise SystemExit(1)
