"""Render a compact visual sheet of MIST expressions and mouth animation states."""

from __future__ import annotations

import json
import re
from pathlib import Path

import cairosvg


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "brain" / "face_assets" / "app" / "app_data.js"
OUTPUT_PATH = ROOT / "output" / "mist-face-collage.png"

EXPRESSIONS = [
    "neutral", "happy", "curious", "thinking", "listening", "surprised",
    "angry", "sad", "panic", "love", "mischief", "proud",
]


def load_data() -> dict:
    source = DATA_PATH.read_text(encoding="utf-8")
    payload = re.search(r"window\.MIST_DATA\s*=\s*(\{.*\});", source, re.S)
    if not payload:
        raise RuntimeError("Could not find MIST_DATA")
    return json.loads(payload.group(1))


def path_data(points: list[list[float]], closed: bool) -> str:
    if closed:
        start = points[0]
        result = f"M {(start[0] + points[-1][0]) / 2:.3f} {(start[1] + points[-1][1]) / 2:.3f}"
        for index, point in enumerate(points):
            other = points[(index + 1) % len(points)]
            result += f" Q {point[0]:.3f} {point[1]:.3f} {(point[0] + other[0]) / 2:.3f} {(point[1] + other[1]) / 2:.3f}"
        return result + " Z"
    result = f"M {points[0][0]:.3f} {points[0][1]:.3f}"
    for index in range(1, len(points) - 1):
        point, other = points[index], points[index + 1]
        result += f" Q {point[0]:.3f} {point[1]:.3f} {(point[0] + other[0]) / 2:.3f} {(point[1] + other[1]) / 2:.3f}"
    return result + f" L {points[-1][0]:.3f} {points[-1][1]:.3f}"


def face_svg(data: dict, expression: str, x: int, y: int, scale: int = 3) -> str:
    mapping = data["faces"]
    face = next(item for item in mapping if item["id"] == expression)
    paths = []
    for role in ("eye_L", "eye_R", "mouth"):
        slot = face["slots"].get(role)
        if not slot:
            continue
        part = data["parts"][slot["part"]]
        angle = slot.get("rot", 0) * 3.141592653589793 / 180
        cos_angle, sin_angle = __import__("math").cos(angle), __import__("math").sin(angle)
        points = []
        for raw_x, raw_y in part["points"]:
            raw_x *= -1 if slot.get("mirror") else 1
            points.append([
                slot["x"] + cos_angle * raw_x - sin_angle * raw_y,
                slot["y"] + sin_angle * raw_x + cos_angle * raw_y,
            ])
        d = path_data(points, part["kind"] == "fill")
        fill = "#5eeadd" if part["kind"] == "fill" else "none"
        stroke = "#5eeadd" if part["kind"] != "fill" else "none"
        paths.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{part.get("width", 0)}" stroke-linecap="round" stroke-linejoin="round"/>')
    label = expression.split("_", 1)[-1].replace("_manual", "").replace("_", " ")
    return f'<g transform="translate({x} {y}) scale({scale})"><rect width="100" height="64" rx="5" fill="#07090c" stroke="#263c3b"/><g>{"".join(paths)}</g><text x="50" y="61" text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="4.2" fill="#a8c9c5">{label}</text></g>'


def mouth_svg(data: dict, name: str, x: int, y: int) -> str:
    points = data["visemes"][name]["points"]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    factor = min(42 / max(width, 1), 25 / max(height, 1))
    transformed = [[50 + (px - (min(xs) + max(xs)) / 2) * factor, 32 + (py - (min(ys) + max(ys)) / 2) * factor] for px, py in points]
    d = path_data(transformed, True)
    return f'<g transform="translate({x} {y})"><rect width="100" height="64" rx="5" fill="#07090c" stroke="#263c3b"/><path d="{d}" fill="#5eeadd"/><text x="50" y="58" text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="5" fill="#a8c9c5">{name}</text></g>'


def main() -> None:
    data = load_data()
    primary = json.loads((ROOT / "brain" / "face_assets" / "face_map.json").read_text(encoding="utf-8"))["expressions"]
    width, height = 1600, 1040
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#101416"/>', '<text x="60" y="70" font-family="Segoe UI, sans-serif" font-size="34" font-weight="600" fill="#d4dfdf">MIST brain interface</text>', '<text x="60" y="105" font-family="Segoe UI, sans-serif" font-size="17" fill="#849494">Expression vocabulary and the single-mouth speech animation path</text>']
    for index, name in enumerate(EXPRESSIONS):
        col, row = index % 4, index // 4
        pieces.append(face_svg(data, primary[name]["primary"], 60 + col * 370, 145 + row * 215, 3.35))
    pieces.extend(['<text x="60" y="820" font-family="Segoe UI, sans-serif" font-size="22" fill="#a8c9c5">Speech animation states: one visible mouth, clocked through visemes</text>'])
    for index, name in enumerate(("rest", "MBP", "FV", "AA", "EH", "EE", "OH", "OO", "S", "LNT")):
        pieces.append(mouth_svg(data, name, 60 + index * 152, 850))
    pieces.append("</svg>")
    svg = "".join(pieces)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(OUTPUT_PATH), output_width=width, output_height=height)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()