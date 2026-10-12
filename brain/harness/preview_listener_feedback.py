"""Local-only UI preview for cached MIST listener acknowledgement cues.

Run this on port 9064, connect the test UI to ``qwen-low``, then POST to
``/replay/start`` with the same-origin header. This uses a fictional caption,
synthetic PCM activity timestamps, the production CascadeVoice listener policy,
and the real cached clips. STT, model, and TTS provider workers are disabled.
"""
from __future__ import annotations

import argparse
import asyncio
import math
from pathlib import Path
import struct
import sys
import tempfile
import time
from types import SimpleNamespace

from aiohttp import web

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN / 'harness'))

from benchmarks.naturalness.cascade_voice import CascadeVoice
from duplex import live_studio


class PreviewMask:
    """The studio's speech mask interface with every network action disabled."""

    def __init__(self, _key, emit):
        self.emit = emit
        self.pending = {}
        self.epoch = 0
        self.muted = False
        self.closed = False

    async def start(self): pass
    async def warm(self): pass
    async def feed(self, _pcm): pass
    async def close(self): self.closed = True
    async def interrupt(self): self.epoch += 1
    def diagnostic(self, *_args, **_kwargs): pass


class PreviewCascade(CascadeVoice):
    """Keep CascadeVoice's real listener and policy; skip provider startup."""

    async def start(self):
        self.loop = asyncio.get_running_loop()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        await self.emit({'type': 'ready', 'listener_ack_supported': True,
                         'preview_mode': 'local_synthetic_listener_feedback'})

    async def close(self):
        # CascadeVoice.close is safe with its never-created provider client;
        # retain its normal timer/listener cleanup and make that contract clear.
        if self.client is None:
            self.socket = self.http = None
        await super().close()


def _is_same_origin_loopback(request: web.Request) -> bool:
    host = request.host.lower()
    return (request.remote in ('127.0.0.1', '::1')
            and host.startswith(('127.0.0.1:', 'localhost:', '[::1]:'))
            and request.headers.get('Origin') == f'http://{request.host}')


def _synthetic_voiced_pcm(duration_s: float = 0.02) -> bytes:
    """A low-level deterministic PCM activity marker; no audio is captured."""
    count = round(16000 * duration_s)
    return b''.join(struct.pack('<h', round(1100 * math.sin(2 * math.pi * 180 * i / 16000)))
                    for i in range(count))


async def _replay(app: web.Application, session) -> None:
    listener = session.voice.listener
    captions = (
        "I'm sketching a fictional herb garden,",
        "I'm sketching a fictional herb garden, and the first choice is a sheltered corner,",
        "I'm sketching a fictional herb garden, and the first choice is a sheltered corner with gentle morning light,",
        "I'm sketching a fictional herb garden, and the first choice is a sheltered corner with gentle morning light, because I want the pots to be easy to reach,",
        "I'm sketching a fictional herb garden, and the first choice is a sheltered corner with gentle morning light, because I want the pots to be easy to reach, and I'd group mint away from the other herbs,",
        "I'm sketching a fictional herb garden, and the first choice is a sheltered corner with gentle morning light, because I want the pots to be easy to reach, and I'd group mint away from the other herbs since it spreads quickly,",
        "I'm sketching a fictional herb garden, and the first choice is a sheltered corner with gentle morning light, because I want the pots to be easy to reach, and I'd group mint away from the other herbs since it spreads quickly, and I'd keep the layout simple because",
    )
    await session.emit({'type': 'preview_fixture', 'synthetic': True,
                        'caption': 'Fictional garden planning; no private conversation is replayed.',
                        'continuous_speech_s': 6.0})
    started = time.monotonic()
    frame = _synthetic_voiced_pcm()
    for index, caption in enumerate(captions):
        await listener.partial(caption)
        deadline = started + (index + 1) if index < len(captions) - 1 else started + 6.0
        while time.monotonic() < deadline:
            if not session.alive:
                app['preview_replay_task'] = None
                return
            listener.note_pcm(frame)
            await asyncio.sleep(min(.10, max(0, deadline - time.monotonic())))

    # Leave a realistic brief pause so the production eligibility timer can
    # choose and deliver the cached cue under its normal freshness checks.
    await asyncio.sleep(.44)
    if not session.alive:
        app['preview_replay_task'] = None
        return
    cue_deadline = time.monotonic() + 1.8
    while listener.pending is None and listener.sent_floor != listener.floor_id:
        if time.monotonic() >= cue_deadline:
            break
        await asyncio.sleep(.04)
    while listener.pending is not None and time.monotonic() < cue_deadline:
        await asyncio.sleep(.04)
    if listener.pending is not None:
        await listener.cancel('preview_receipt_timeout')
    await listener.finish(
        "That is the fictional garden plan: a sheltered herb corner with morning light, easy access, and mint kept in its own pot."
    )
    await session.emit({'type': 'preview_fixture_complete', 'synthetic': True,
                        'elapsed_s': round(time.monotonic() - started, 3)})
    app['preview_replay_task'] = None


def create_preview(run_dir: Path) -> web.Application:
    """Create the real trial UI/app with a local-only voice and mask factory."""
    args = SimpleNamespace(run_dir=run_dir)
    # TrialConversation looks up this module symbol when it constructs the
    # speech mask. The replacement has no HTTP or WebSocket provider methods.
    live_studio.StreamingTTS = PreviewMask
    app = live_studio.create_studio(args)
    app['trial_voice_factory'] = PreviewCascade
    app['preview_replay_task'] = None
    app['preview_mode'] = 'All input below is synthetic and fictional; no speech providers are called.'
    # Make the architecture selector usable offline. These placeholders only
    # satisfy the catalogue's key-presence check and reach PreviewMask only.
    app['env'].update(ELEVENLABS_API_KEY='preview-disabled',
                      DEEPGRAM_API_KEY='preview-disabled', CEREBRAS_API_KEY='preview-disabled')

    async def replay_start(request: web.Request):
        if not _is_same_origin_loopback(request):
            raise web.HTTPForbidden(text='Use the local test page on this origin.')
        if request.content_length not in (None, 0) and request.content_length > 512:
            raise web.HTTPRequestEntityTooLarge(max_size=512, actual_size=request.content_length)
        owner = app.get('trial_owner')
        session = owner.get('session') if owner else None
        if not session or not session.started or not isinstance(session.voice, PreviewCascade):
            raise web.HTTPConflict(text='Connect the local test UI session first.')
        task = app.get('preview_replay_task')
        if task is not None and not task.done():
            raise web.HTTPConflict(text='A synthetic preview is already running.')
        if session.voice.listener_voice.event_for('mhm') is None:
            raise web.HTTPServiceUnavailable(text='The cached MIST listening cue is unavailable.')
        app['preview_replay_task'] = asyncio.create_task(_replay(app, session))
        return web.json_response({'accepted': True, 'synthetic': True,
                                  'disclosure': app['preview_mode'],
                                  'fixture': 'six-second fictional garden explanation, short pause, final caption'})

    app.router.add_post('/replay/start', replay_start)

    async def stop_replay(_app):
        task = app.get('preview_replay_task')
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        app['preview_replay_task'] = None

    app.on_cleanup.append(stop_replay)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=9064)
    parser.add_argument('--run-dir', type=Path)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('--port must be between 1024 and 65535')
    if args.run_dir is None:
        temp_root = Path(tempfile.mkdtemp(prefix='mist-listener-preview-'))
        run_dir = temp_root / 'results'
    else:
        run_dir = args.run_dir.resolve()
    app = create_preview(run_dir)
    print(f'Local synthetic preview: http://127.0.0.1:{args.port}/try', flush=True)
    print(f'POST http://127.0.0.1:{args.port}/replay/start with Origin: http://127.0.0.1:{args.port}', flush=True)
    print(f'Isolated results: {run_dir}', flush=True)
    web.run_app(app, host='127.0.0.1', port=args.port, print=None)


if __name__ == '__main__':
    main()
