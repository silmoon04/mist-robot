# CAD tooling intake, 12 September 2026

Fusion is running and its local MCP responds. This intake reused the existing MCP client and installed Python environments only. It did not import or modify earlier robot geometry.

## Fusion state

- Fusion version: `2705.1.11`.
- MCP endpoint: `http://127.0.0.1:27182/mcp`.
- One active `Untitled` document, unsaved and unmodified.
- Active Fusion design available, zero root bodies and zero occurrences.
- Default `SelectCommand` active, with no modeling dialog open.
- `adsk.fusion.TemporaryBRepManager` available.

The endpoint was initially closed because Fusion was not running. The normal installed launcher was started with `Start-Process -WindowStyle Hidden`. Fusion showed its Recovered Documents dialog, which blocked the first read call. Clicking Close dismissed that dialog and preserved its recovery files. Subsequent document, command and read-only script queries succeeded.

Launcher: `<LOCAL_HOME>/AppData/Local/Autodesk/webdeploy/production/6a0c9611291d45bb9226980209917c3d/FusionLauncher.exe`.

## MCP contract

The inspected client is `design/mist_v2_20260906/cad/fusion_live_20260907/client.py`. It initializes MCP protocol `2025-03-26`, preserves the session header and exposes `FusionClient.call(name, arguments)`. Available tools are `fusion_mcp_read`, `fusion_mcp_execute`, `fusion_mcp_electronics_read` and `fusion_mcp_update`.

Read document state with `fusion_mcp_read` arguments `{"queryType":"document","operation":"open"}`. Read the active dialog with `{"queryType":"activeCommand"}`.

Execute native Python with `fusion_mcp_execute` arguments `{"featureType":"script","object":{"script":"..."}}`. The script must define `def run(_context: str):`. Printed output is returned in a text content block. Set `object.readOnly` to `true` only for a script that creates, modifies and deletes nothing. Fusion enforces this flag. Do not use `Application.executeTextCommand` from a read-only script.

The client command for a native script file is:

```powershell
python design/mist_v2_20260906/cad/fusion_live_20260907/client.py --script <new-script-path> --output <new-response-path> --timeout 180
```

That command hashes the source before dispatch, loads it as a real module and calls its `run` function. It writes a JSON response, so register that output with the punctuation hook before final handover. Mutations must have a single owner and must not be retried automatically after timeout; inspect the document and progress files first.

The `apiDocumentation` query accepted `BRepBodies.add` but returned no member detail. Use the installed API stubs or official Autodesk API reference when a query returns no documentation.

## Verified Python environments

All project paths below begin at `/`.

| Executable | Verified packages and result |
| --- | --- |
| `design/mist_v2_20260906/coupons/.venv_stable/Scripts/python.exe` | CadQuery 2.6.1, OCP 7.8.1.1, trimesh 4.7.4, matplotlib and Pillow. A CadQuery 1 x 2 x 3 box was valid with volume 6, but the interpreter exited with code 1 during shutdown. |
| `design/mist_v2_20260906/coupons/.venv/Scripts/python.exe` | CadQuery 2.8.0, OCP 7.9.3.1, trimesh 5.1.0, matplotlib and Pillow. The same box result succeeded, with the same exit code 1. |
| `design/mist_v2_20260906/simulation/.venv/Scripts/python.exe` | PyBullet API version 202010061. Connecting with `DIRECT` and disconnecting succeeded with exit code 0. CadQuery, OCP, trimesh and matplotlib are absent. |
| `<LOCAL_HOME>/anaconda3/python.exe` | trimesh 4.12.2, matplotlib 3.9.2, Pillow 12.0.0 and pyrender 0.1.45 imported with exit code 0. CadQuery, OCP and PyBullet are absent. |

A direct OCP test in `.venv_stable` used `BRepPrimAPI_MakeBox(1,2,3)` and `BRepCheck_Analyzer`; it returned a valid shape and exited with code 0. This isolates the observed shutdown problem to the broader CadQuery import path. Do not mask a failing process exit code or equate a written export with a clean generator run. Independent mesh checks can use the base Python environment, and native Fusion checks remain separate.

The bundled general runtime is `<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. Its CAD package availability was not tested.
