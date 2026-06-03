"""Rasterise the weather-condition icons from Meteocons SVGs to PNG (build-time).

This is NOT needed to run the pipeline — the resulting PNGs are committed under
assets/icons/. Re-run it only to refresh or change the icon set.

    pip install cairosvg
    python tools/render_icons.py

Icons: Meteocons by Bas Milius (MIT) — https://github.com/basmilius/weather-icons
"""
from __future__ import annotations

import io
import os
import urllib.request

import cairosvg
from PIL import Image

BASE = "https://cdn.jsdelivr.net/npm/@bybas/weather-icons@2.0.0/production/fill/all"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
SIZE = 256

# our normalized condition -> ordered Meteocons candidates (first that exists wins)
WANT = {
    "sun":     ["clear-day"],
    "partly":  ["partly-cloudy-day"],
    "cloud":   ["cloudy", "overcast-day", "overcast"],
    "fog":     ["fog-day", "fog", "mist", "haze-day"],
    "rain":    ["rain", "partly-cloudy-day-rain", "overcast-day-rain"],
    "thunder": ["thunderstorms-day-rain", "thunderstorms-rain", "thunderstorms-day"],
}


def _exists(name: str) -> bool:
    try:
        req = urllib.request.Request(f"{BASE}/{name}.svg", method="HEAD")
        return urllib.request.urlopen(req, timeout=15).status == 200
    except Exception:
        return False


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for cond, names in WANT.items():
        chosen = next((n for n in names if _exists(n)), None)
        if not chosen:
            print(f"{cond}: no candidate found from {names}")
            continue
        png = cairosvg.svg2png(url=f"{BASE}/{chosen}.svg", output_width=SIZE, output_height=SIZE)
        Image.open(io.BytesIO(png)).convert("RGBA").save(os.path.join(OUT, f"{cond}.png"))
        print(f"{cond}: {chosen}.svg -> assets/icons/{cond}.png")


if __name__ == "__main__":
    main()
