# Managed console startup

This change applies to the next authorized launch. The live console on port 8776, PID 50488, and recognition proxy on port 8788, PID 50852, were not stopped, restarted or adopted. Their listener identities are recorded in `live_unchanged.json`.

## Normal launch

From `brain`, use one command:

```powershell
python ui/server.py --port 8776 --run-dir results/mist-v2-browser-live
```

The default managed mode starts the HTTP console and streaming-recognition proxy in the same Python process. Console and proxy ports default to 8776 and 8788. `--port` and `--stt-port` configure another pair; proxy origins derive from the actual console port, and the selected proxy URL is advertised through `/api/config`. The only browser-code change passes that advertised URL to the existing streaming client. When talking to the unchanged live server, the client retains its previous 8788 fallback.

Both ports are reserved before the model client is constructed or queued background jobs start. A conflicting listener, missing streaming dependency or fresh foreign worker heartbeat causes startup to fail while releasing only newly owned resources. The launcher does not enumerate or terminate processes and does not silently attach to an occupied port.

Ctrl+C routes through `ConsoleRuntime.close()`. It stops the owned HTTP and proxy loops, closes browser SSE and WebSocket connections, cancels owned background jobs, closes the model client and joins its service threads. Proxy engine creation is lazy: reserving the listener does not create a provider client. `--stt-mode external` explicitly leaves an independently managed proxy alone, and `--stt-mode off` uses batch recognition only. Stub and watch launches default to off.

Managed mode uses the validated `websockets` 13.1 dependency, pinned in `brain/ui/requirements-stt.txt`. The console and streaming guides document installation, custom ports and external ownership.

## Failures reproduced during validation

The first duplicate-console test found that Windows HTTP address reuse allowed two runtimes to share one HTTP port. The console now requests exclusive Windows socket ownership. The regression verifies the second launch fails before constructing another backend client while the first remains usable.

Review also exposed a shutdown race. A fake speech-engine factory was paused after WebSocket acceptance. Shutdown returned before the factory completed; once released, the old browser could start an utterance. The proxy now marks itself stopping before shutdown, closes the pending browser connection, and rejects publication of an engine created after that point. The late engine is closed rather than exposed.

## Evidence

Twenty lifecycle tests pass using fake engines, stub clients, temporary directories and ephemeral loopback ports. They exercise the actual normal CLI and managed runtime, both socket reservations, matched 127.0.0.1 and localhost origins, one-browser ownership, active-engine and SSE closure, job and heartbeat cleanup, late engine construction, startup failure, duplicate listeners, external ownership and idempotent shutdown.

The complete offline runner also passed after integration. `offline_checks.txt` contains the output. No real microphone, paid provider, language-model call or live service shutdown was used for these lifecycle tests.

Changed implementation: `brain/ui/server.py`, `brain/ui/stt_proxy.py`, the proxy-URL argument in `brain/ui/static/index.html`, the new lifecycle test and dependency file, and the startup documentation. The currently running pair remains separately managed until a later authorized launch uses this lifecycle.
