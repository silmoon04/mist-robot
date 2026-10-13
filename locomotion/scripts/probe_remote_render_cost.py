"""Time exactly one isolated interactive reset frame, without a worker or server."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from locomotion import sim_remote as legacy
from locomotion import sim_remote_interactive as interactive


def measure():
    render = interactive.MistEnv.render
    save = interactive.Image.Image.save
    raster_times, encoding_times = [], []
    frame_start, frame_end = [], []

    def timed_render(env, *args, **kwargs):
        start = time.perf_counter()
        frame_start.append(start)
        result = render(env, *args, **kwargs)
        raster_times.append(time.perf_counter() - start)
        return result

    def timed_save(image, *args, **kwargs):
        start = time.perf_counter()
        result = save(image, *args, **kwargs)
        end = time.perf_counter()
        encoding_times.append(end - start)
        frame_end.append(end)
        return result

    with patch.object(legacy.threading.Thread, "start"), \
            patch.object(interactive.MistEnv, "render", timed_render), \
            patch.object(interactive.Image.Image, "save", timed_save):
        simulation = interactive.InteractiveSimulation()
    try:
        if len(frame_start) != 1 or len(frame_end) != 1:
            raise AssertionError("Expected exactly one rendered and encoded reset frame")
        env, bullet = simulation.env, interactive.p
        bodies = [env._call(bullet.getBodyUniqueId, index)
                  for index in range(env._call(bullet.getNumBodies))]
        landmarks = set(bodies) - {env.robot, env.floor}
        if len(landmarks) != 1:
            raise AssertionError("Expected one combined landmark mesh")
        body = next(iter(landmarks))
        if env._call(bullet.getCollisionShapeData, body, -1):
            raise AssertionError("Landmarks must have no collision geometry")
        if env._call(bullet.getDynamicsInfo, body, -1)[0] != 0:
            raise AssertionError("Landmarks must have zero mass")
        visuals = env._call(bullet.getVisualShapeData, body)
        if len(visuals) != 1 or visuals[0][2] != bullet.GEOM_MESH:
            raise AssertionError("Expected one visual mesh")
        paths = [Path(__file__).resolve(), Path(interactive.__file__), interactive.PROFILE_PATH]
        return {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "One isolated reset frame; background worker disabled; no server or control steps",
            "limitations": "Single cold frame at reset pose, not sustained throughput or a paired pose comparison",
            "profile": interactive.PROFILE,
            "total_rendered_frames": 1,
            "control_steps": 0,
            "landmark_visual_bodies": len(landmarks),
            "landmarks_mass_zero_and_collision_free": True,
            "render_ms": raster_times[0] * 1000,
            "jpeg_encode_ms": encoding_times[0] * 1000,
            "render_through_jpeg_ms": (frame_end[0] - frame_start[0]) * 1000,
            "source_sha256": {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in paths},
        }
    finally:
        simulation.running = False
        simulation.env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = measure()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
