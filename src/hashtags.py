"""Weather / Bangladesh hashtags, used a block at a time in rotating order.

`BRAND_TAG` is added to every post on top of the rotating block (see main.py),
so each caption gets the brand tag + PER_POST rotating tags. Rotating the block
each post keeps captions from being byte-identical run to run.
"""

BRAND_TAG = "bdweather"            # always included, on top of the rotating block
PER_POST = 6

HASHTAGS = [
    # core weather
    "weather", "weatherupdate", "bangladeshweather", "bdweather", "todayweather",
    "temperature", "forecast", "weatherforecast", "dailyweather", "climate",
    "abohawa", "আবহাওয়া", "তাপমাত্রা", "বাংলাদেশ", "weatherbangladesh",
    # divisions
    "dhaka", "chattogram", "chittagong", "rajshahi", "khulna",
    "barishal", "sylhet", "rangpur", "mymensingh", "ঢাকা",
    # country / general
    "bangladesh", "bd", "heatwave", "monsoon", "rain",
    "summer", "winter", "humidity", "metoffice", "weatherreport",
]


def block_at(cursor: int) -> list[str]:
    """Return PER_POST hashtags starting at `cursor` (wrapping around the list)."""
    n = len(HASHTAGS)
    c = cursor % n
    return [HASHTAGS[(c + i) % n] for i in range(PER_POST)]


def render(cursor: int) -> str:
    """'#bdweather #tag1 #tag2 ...' for the block at `cursor`."""
    tags = [BRAND_TAG] + block_at(cursor)
    # de-dup while preserving order (BRAND_TAG may also appear in the block)
    seen, ordered = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return " ".join(f"#{t}" for t in ordered)
