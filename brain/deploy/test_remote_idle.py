"""One opt-in, input-free authenticated trial WebSocket retention probe."""
import argparse
import asyncio
import json
from pathlib import Path
import time

import aiohttp

from test_remote_e2e import Attempt, base_origin, receive_until


async def main(args):
    base = base_origin(args.base)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    attempt = Attempt('idle_websocket', out)
    result = {'base': base, 'duration_target_s': 90, 'ping_interval_s': 10,
              'pongs': [], 'ready': False, 'closed_cleanly': False, 'failures': []}
    ws = None
    try:
        code = Path(args.pair_code_file).read_text(encoding='ascii').strip()
        if len(code) < 32:
            raise ValueError('Pair code too short')
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10),
                                         cookie_jar=aiohttp.CookieJar()) as http:
            async with http.post(base + '/trial/pair', json={'code': code}, headers={'Origin': base}) as response:
                if response.status != 200:
                    raise RuntimeError(f'Pairing HTTP {response.status}')
            async with http.post(base + '/trial/bootstrap', json={}, headers={'Origin': base}) as response:
                if response.status != 200:
                    raise RuntimeError(f'Bootstrap HTTP {response.status}')
            ws = await http.ws_connect(base + '/trial/voice?architecture=qwen-affect',
                                       headers={'Origin': base}, heartbeat=20, timeout=45)
            try:
                await receive_until(ws, attempt, lambda event, _: event.get('type') == 'ready', 45)
                result['ready'] = True
                started = time.monotonic()
                for index in range(10):
                    await asyncio.sleep(max(0, started + index * 10 - time.monotonic()))
                    sent = time.monotonic()
                    await ws.send_json({'type': 'ping'})
                    await receive_until(ws, attempt, lambda event, _: event.get('type') == 'pong', 5)
                    result['pongs'].append({'index': index, 'at_s': round(sent - started, 3),
                                            'rtt_ms': round((time.monotonic() - sent) * 1000)})
                # Observe the final interval too; an unexpected close is a failure.
                try:
                    await receive_until(ws, attempt, lambda event, _: False,
                                        max(0.01, started + 90 - time.monotonic()))
                except TimeoutError:
                    pass
                result['observed_s'] = round(time.monotonic() - started, 3)
            finally:
                try:
                    await asyncio.wait_for(ws.close(), 10)
                    result['websocket_closed'] = ws.closed
                except Exception as error:
                    result['failures'].append(f'WebSocket close: {type(error).__name__}')
                try:
                    async with http.post(base + '/trial/disconnect', json={}, headers={'Origin': base},
                                         timeout=aiohttp.ClientTimeout(total=20)) as response:
                        result['disconnect_status'] = response.status
                except Exception as error:
                    result['failures'].append(f'Disconnect: {type(error).__name__}')
                if attempt.trace_id:
                    try:
                        async with http.get(base + '/trial/export', params={'session': attempt.trace_id},
                                            timeout=aiohttp.ClientTimeout(total=10)) as response:
                            result['export_status'] = response.status
                            if response.status == 200:
                                result['session_status'] = (await response.json()).get('session', {}).get('status')
                    except Exception as error:
                        result['failures'].append(f'Export: {type(error).__name__}')
    except Exception as error:
        result['failures'].append(f'{type(error).__name__}: {str(error)[:240]}')
    result['trace_id'] = attempt.trace_id
    result['closed_cleanly'] = result.get('websocket_closed') is True and \
        result.get('disconnect_status') == 200 and result.get('session_status') == 'ended'
    result['success'] = result['ready'] and len(result['pongs']) == 10 and \
        result.get('observed_s', 0) >= 90 and result['closed_cleanly'] and not result['failures']
    attempt.finish({'ready': result['ready'], 'closed_cleanly': result['closed_cleanly']})
    (out / 'idle-summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['success'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--pair-code-file', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        raise SystemExit('--run is required for the network probe')
    raise SystemExit(asyncio.run(main(args)))
