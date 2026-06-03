"""Fetch temperatures for Bangladesh's 8 divisions from Meteosource.

One request per divisional HQ city (8 per run) to the free `point` endpoint,
pulling the current temperature + condition and today's forecast min/max.

Free tier (https://www.meteosource.com/): 400 calls/day, 10/min — comfortably
above our 8 divisions × 4 posts/day = 32 calls/day. Requires an API key in
METEOSOURCE_API_KEY; free/non-commercial use needs an attribution backlink
(added to the caption — see main.py). Docs: https://www.meteosource.com/documentation
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass

import requests

API = "https://www.meteosource.com/api/v1/free/point"
TIMEOUT = 20
TZ = "Asia/Dhaka"
SOURCE = "Meteosource"
SOURCE_URL = "https://www.meteosource.com"

# Each division keyed by its administrative seat (the divisional HQ city).
# (bangla name, english name, latitude, longitude). Order = display order.
DIVISIONS: list[tuple[str, str, float, float]] = [
    ("ঢাকা", "Dhaka", 23.8103, 90.4125),
    ("চট্টগ্রাম", "Chattogram", 22.3569, 91.7832),
    ("রাজশাহী", "Rajshahi", 24.3636, 88.6241),
    ("খুলনা", "Khulna", 22.8456, 89.5403),
    ("বরিশাল", "Barishal", 22.7010, 90.3535),
    ("সিলেট", "Sylhet", 24.8949, 91.8687),
    ("রংপুর", "Rangpur", 25.7439, 89.2752),
    ("ময়মনসিংহ", "Mymensingh", 24.7471, 90.4203),
]

# Normalised sky conditions used by the card renderer.
CONDITIONS = ("sun", "partly", "cloud", "fog", "rain", "thunder")


@dataclass
class DivisionWeather:
    name_bn: str
    name_en: str
    current: float | None       # current temperature, °C
    tmin: float | None          # today's forecast low, °C
    tmax: float | None          # today's forecast high, °C
    condition: str = "cloud"    # one of CONDITIONS (for the icon + label)


@dataclass
class WeatherReport:
    divisions: list[DivisionWeather]
    fetched_at: _dt.datetime
    source: str = SOURCE
    source_url: str = SOURCE_URL


def _normalize_condition(icon: str | None) -> str:
    """Map a Meteosource icon string (e.g. 'mostly_cloudy') to our 6 categories."""
    s = (icon or "").lower()
    if "thunder" in s:
        return "thunder"
    if "rain" in s or "drizzle" in s or "shower" in s or "snow" in s or "hail" in s:
        return "rain"               # BD rarely snows; show precip as rain
    if "fog" in s or "mist" in s:
        return "fog"
    if "overcast" in s or "cloudy" in s:
        return "cloud"
    if "partly" in s:
        return "partly"
    if "sunny" in s or "clear" in s:
        return "sun"
    return "cloud"


def _api_key() -> str:
    key = os.environ.get("METEOSOURCE_API_KEY")
    if not key:
        raise RuntimeError(
            "METEOSOURCE_API_KEY is not set. Get a free key at "
            "https://www.meteosource.com/ and put it in .env (or the environment)."
        )
    return key


def _fetch_point(lat: float, lon: float, key: str) -> dict:
    resp = requests.get(
        API,
        params={"lat": f"{lat:.4f}", "lon": f"{lon:.4f}",
                "sections": "current,daily", "units": "metric", "key": key},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_report(divisions=DIVISIONS) -> WeatherReport:
    """Query Meteosource for every division. Raises if the API key is missing."""
    key = _api_key()
    out: list[DivisionWeather] = []
    for name_bn, name_en, lat, lon in divisions:
        try:
            data = _fetch_point(lat, lon, key)
        except Exception:
            out.append(DivisionWeather(name_bn, name_en, None, None, None))
            continue
        cur = data.get("current") or {}
        current = cur.get("temperature")
        condition = _normalize_condition(cur.get("icon"))
        day0 = ((data.get("daily") or {}).get("data") or [{}])[0]
        all_day = day0.get("all_day") or {}
        tmin = all_day.get("temperature_min")
        tmax = all_day.get("temperature_max")
        out.append(DivisionWeather(
            name_bn, name_en,
            float(current) if current is not None else None,
            float(tmin) if tmin is not None else None,
            float(tmax) if tmax is not None else None,
            condition,
        ))

    # Meteosource times are per-point; the local Dhaka clock is fine for the slot.
    now_dhaka = _dt.datetime.utcnow() + _dt.timedelta(hours=6)
    return WeatherReport(divisions=out, fetched_at=now_dhaka)


if __name__ == "__main__":
    rep = fetch_report()
    print(f"as of {rep.fetched_at:%Y-%m-%d %H:%M}  ({rep.source})")
    for d in rep.divisions:
        print(f"  {d.name_en:12s} now={d.current}  low={d.tmin}  high={d.tmax}  {d.condition}")
