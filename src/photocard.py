"""Render a 720x900 (4:5) Bangla weather card for all 8 Bangladesh divisions.

A bright, clean weather-app look: a soft sky-tinted background, a 2x4 grid of
white cards with gentle drop shadows — one per division — each with a drawn
weather-condition icon, the division name, a large current temperature
(colour-coded by heat) and the day's low / high. A pulsing dot in the header
chip animates the video.

Everything user-facing is in Bangla (Noto Sans Bengali, complex-shaped via raqm).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import bangla
from .weather import WeatherReport

W, H = 720, 900               # default card size (4:5 portrait)
_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_PATH = os.path.join(_ASSETS, "fonts", "NotoSansBengali.ttf")
LOGO_PATH = os.path.join(_ASSETS, "logo.png")   # optional brand logo (BWN)

BRAND = "বাংলাদেশ আবহাওয়া"   # title shown on every card


@dataclass
class Theme:
    bg_top: tuple
    bg_bottom: tuple
    card_bg: tuple
    card_border: tuple
    ink: tuple              # primary text on cards
    subink: tuple           # muted secondary text
    accent: tuple           # chip / header bar
    live: tuple             # pulsing dot
    shadow: tuple           # RGBA card shadow
    header_ink: tuple       # title text colour (on the background)
    header_sub: tuple       # date text colour (on the background)
    logo_badge: bool        # white badge behind the logo (for dark backgrounds)


THEMES: dict[str, Theme] = {
    # 1) Vibrant indigo→plum gradient, crisp white cards
    "aurora": Theme(
        bg_top=(58, 60, 158), bg_bottom=(168, 70, 140),
        card_bg=(255, 255, 255), card_border=(255, 255, 255),
        ink=(32, 38, 76), subink=(120, 128, 156),
        accent=(124, 92, 240), live=(80, 230, 160),
        shadow=(20, 16, 50, 80), header_ink=(255, 255, 255),
        header_sub=(226, 224, 245), logo_badge=True,
    ),
    # 2) BWN brand: ocean-blue → teal-green gradient, white cards
    "brand": Theme(
        bg_top=(14, 74, 124), bg_bottom=(18, 132, 110),
        card_bg=(255, 255, 255), card_border=(255, 255, 255),
        ink=(20, 44, 70), subink=(110, 126, 142),
        accent=(16, 160, 120), live=(255, 214, 90),
        shadow=(6, 30, 40, 80), header_ink=(255, 255, 255),
        header_sub=(214, 236, 230), logo_badge=True,
    ),
    # 3) Minimal: near-white, colour comes only from icons + temps
    "mist": Theme(
        bg_top=(243, 245, 249), bg_bottom=(233, 237, 243),
        card_bg=(255, 255, 255), card_border=(228, 232, 240),
        ink=(28, 38, 60), subink=(132, 140, 158),
        accent=(40, 116, 196), live=(22, 190, 120),
        shadow=(40, 60, 100, 45), header_ink=(28, 38, 60),
        header_sub=(130, 140, 158), logo_badge=False,
    ),
}


@dataclass
class CardStyle:
    brand: str = BRAND
    theme: str = "mist"
    width: int = W
    height: int = H
    accent: tuple | None = None          # unused; kept for CLI compatibility
    headline_size: int | None = None     # unused; kept for CLI compatibility


def _font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(FONT_PATH, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def _load_logo():
    """Load assets/logo.png as a trimmed RGBA image, or None if absent.

    Works whether the PNG is already transparent or sits on a solid black
    background — near-black pixels are made transparent, then padding is cropped.
    """
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        img = Image.open(LOGO_PATH).convert("RGBA")
    except Exception:
        return None
    if img.getchannel("A").getextrema()[0] >= 250:
        px = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if max(r, g, b) < 30:
                    px[x, y] = (r, g, b, 0)
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


# --------------------------------------------------------------------------- #
# Background
# --------------------------------------------------------------------------- #
def _gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h))


# --------------------------------------------------------------------------- #
# Weather-condition icons (bundled Meteocons PNGs, MIT — assets/icons/<cond>.png)
# --------------------------------------------------------------------------- #
_ICON_DIR = os.path.join(_ASSETS, "icons")
_ICON_CACHE: dict[str, Image.Image] = {}


def _condition_bn(cond: str) -> str:
    """Short Bangla label for a normalized sky condition (see weather.CONDITIONS)."""
    if cond == "sun":
        return "রৌদ্রোজ্জ্বল"
    if cond == "partly":
        return "আংশিক মেঘলা"
    if cond == "fog":
        return "কুয়াশা"
    if cond == "rain":
        return "বৃষ্টি"
    if cond == "thunder":
        return "বজ্রসহ বৃষ্টি"
    return "মেঘলা"


def _icon(size: int, cond: str) -> Image.Image:
    """Return an RGBA icon of side `size` for a normalized condition string."""
    src = _ICON_CACHE.get(cond)
    if src is None:
        path = os.path.join(_ICON_DIR, f"{cond}.png")
        if not os.path.exists(path):
            path = os.path.join(_ICON_DIR, "cloud.png")
        src = Image.open(path).convert("RGBA")
        _ICON_CACHE[cond] = src
    return src.resize((size, size), Image.LANCZOS)


def _paste_icon(card: Image.Image, ic: Image.Image, x: int, y: int, s: float) -> None:
    """Composite an icon onto the card with a soft drop shadow.

    The shadow gives light icons (white clouds) definition on a light card,
    so they read clearly without darkening the card itself.
    """
    pad = int(10 * s)
    alpha = ic.getchannel("A")
    shadow = Image.new("RGBA", ic.size, (36, 58, 92, 0))
    shadow.putalpha(alpha.point(lambda a: int(a * 0.42)))
    canvas = Image.new("RGBA", (ic.width + 2 * pad, ic.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(shadow, (pad, pad + int(4 * s)))
    canvas = canvas.filter(ImageFilter.GaussianBlur(int(4 * s)))
    canvas.alpha_composite(ic, (pad, pad))
    card.alpha_composite(canvas, (x - pad, y - pad))


# --------------------------------------------------------------------------- #
# Temperature colour + pulse
# --------------------------------------------------------------------------- #
def _temp_color(c: float | None) -> tuple:
    if c is None:
        return (140, 150, 168)
    if c <= 22:
        return (33, 118, 206)
    if c <= 28:
        return (16, 152, 120)
    if c <= 33:
        return (230, 146, 24)
    if c <= 37:
        return (224, 100, 28)
    return (210, 54, 48)


def _blink_alpha(t: float, hz: float = 1.0) -> float:
    base = 0.5 + 0.5 * math.cos(2 * math.pi * hz * t)
    return 0.2 + 0.8 * (base ** 2)


def _draw_pulse_dot(base: Image.Image, center, r: int, color, alpha: float) -> Image.Image:
    cx, cy = center
    ss = 4
    box = (r * 2 + 2) * ss
    layer = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([ss, ss, box - ss, box - ss], fill=(*color, int(255 * alpha)))
    layer = layer.resize(((r * 2 + 2), (r * 2 + 2)), Image.LANCZOS)
    out = base.convert("RGBA")
    out.alpha_composite(layer, (cx - r - 1, cy - r - 1))
    return out.convert("RGB")


def _tri(d, cx, cy, r, color, up: bool) -> None:
    if up:
        pts = [(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)]
    else:
        pts = [(cx, cy + r), (cx - r, cy - r), (cx + r, cy - r)]
    d.polygon(pts, fill=color)


# --------------------------------------------------------------------------- #
# Compose
# --------------------------------------------------------------------------- #
def _compose(report: WeatherReport, style: CardStyle):
    """Render everything except the pulsing dot. Returns (image, dot_geom)."""
    w, h = style.width, style.height
    s = w / 1080.0
    margin = int(60 * s)

    date_str = bangla.bn_date(report.fetched_at.date())
    slot = bangla.slot_label(report.fetched_at)
    th = THEMES.get(style.theme, THEMES["aurora"])

    card = _gradient(w, h, th.bg_top, th.bg_bottom).convert("RGBA")

    # ---- header geometry -------------------------------------------------
    title_y = int(46 * s)
    chip_font = _font(int(27 * s), "SemiBold")
    chip_tw = chip_font.getlength(slot)
    dot_r = max(5, int(8 * s))
    chip_pad = int(20 * s)
    chip_h = int(52 * s)
    chip_gap = int(12 * s)
    chip_w = int(dot_r * 2 + chip_gap + chip_tw + 2 * chip_pad)
    chip_x1 = w - margin - chip_w
    chip_y0 = title_y + int(2 * s)
    chip_y1 = chip_y0 + chip_h
    chip_cy = (chip_y0 + chip_y1) // 2
    dot_cx = chip_x1 + chip_pad + dot_r

    # ---- grid geometry ---------------------------------------------------
    cols, rows = 2, 4
    gap = int(24 * s)
    grid_top = int(168 * s)
    foot_h = int(50 * s)
    foot_top = h - foot_h
    grid_bottom = foot_top - gap
    card_w = (w - 2 * margin - (cols - 1) * gap) / cols
    card_h = (grid_bottom - grid_top - (rows - 1) * gap) / rows
    radius = int(28 * s)

    cells = []
    for i in range(len(report.divisions)):
        r, c = divmod(i, cols)
        x0 = margin + c * (card_w + gap)
        y0 = grid_top + r * (card_h + gap)
        cells.append([x0, y0, x0 + card_w, y0 + card_h])

    # ---- soft drop shadows under the cards -------------------------------
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    off = int(7 * s)
    for x0, y0, x1, y1 in cells:
        sd.rounded_rectangle([x0, y0 + off, x1, y1 + off], radius=radius, fill=th.shadow)
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(9 * s)))
    card.alpha_composite(shadow)

    draw = ImageDraw.Draw(card)

    # ---- cards -----------------------------------------------------------
    for x0, y0, x1, y1 in cells:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius,
                               fill=th.card_bg, outline=th.card_border, width=max(1, int(1.4 * s)))

    # ---- condition icons -------------------------------------------------
    icon_sz = int(card_h * 0.52)
    for (x0, y0, x1, _y1), dv in zip(cells, report.divisions):
        ic = _icon(icon_sz, dv.condition)
        _paste_icon(card, ic, int(x1 - int(14 * s) - icon_sz), int(y0 + int(10 * s)), s)

    # ---- time-slot chip --------------------------------------------------
    draw.rounded_rectangle([chip_x1, chip_y0, w - margin, chip_y1],
                           radius=chip_h // 2, fill=th.accent)
    draw.text((dot_cx + dot_r + chip_gap, chip_cy), slot,
              font=chip_font, fill=(255, 255, 255), anchor="lm")
    dot_geom = ((dot_cx, chip_cy), dot_r, th.live)

    # ---- header: logo (if present) + title + date -----------------------
    title_font = _font(int(54 * s), "ExtraBold")
    sub_font = _font(int(28 * s), "Medium")
    logo = _load_logo()
    if logo is not None:
        logo_h = int(116 * s)
        logo_w = max(1, int(logo.width * (logo_h / logo.height)))
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        logo_y = title_y - int(12 * s)
        if th.logo_badge:                       # white badge for dark backgrounds
            bpad = int(12 * s)
            draw.rounded_rectangle(
                [margin - bpad // 2, logo_y - bpad // 2,
                 margin + logo_w + bpad, logo_y + logo_h + bpad // 2],
                radius=int(18 * s), fill=(255, 255, 255, 255))
        card.alpha_composite(logo, (margin, logo_y))
        tx = margin + logo_w + (int(26 * s) if th.logo_badge else int(18 * s))
    else:
        bar_w = max(5, int(11 * s))
        draw.rectangle([margin, title_y + int(4 * s), margin + bar_w,
                        title_y + int(52 * s)], fill=th.accent)
        tx = margin + bar_w + int(16 * s)
    draw.text((tx, title_y), style.brand, font=title_font, fill=th.header_ink)
    draw.text((tx, title_y + int(58 * s)), date_str, font=sub_font, fill=th.header_sub)

    # ---- per-card content ------------------------------------------------
    name_font = _font(int(34 * s), "Bold")
    temp_font = _font(int(76 * s), "ExtraBold")
    cond_font = _font(int(25 * s), "Medium")
    lh_font = _font(int(26 * s), "SemiBold")
    pad = int(24 * s)

    for (x0, y0, x1, y1), dv in zip(cells, report.divisions):
        draw.text((x0 + pad, y0 + int(18 * s)), dv.name_bn, font=name_font, fill=th.ink)
        draw.text((x0 + pad - int(2 * s), y0 + int(56 * s)), bangla.temp_bn(dv.current),
                  font=temp_font, fill=_temp_color(dv.current))
        draw.text((x0 + pad, y0 + int(148 * s)), _condition_bn(dv.condition),
                  font=cond_font, fill=th.subink)
        ly = y1 - pad - int(6 * s)
        tri_r = int(8 * s)
        cx = x0 + pad + tri_r
        _tri(draw, cx, ly, tri_r, (44, 110, 200), up=False)
        lo = bangla.temp_bn(dv.tmin)
        draw.text((cx + tri_r + int(8 * s), ly), lo, font=lh_font, fill=(44, 110, 200), anchor="lm")
        gap_x = cx + tri_r + int(8 * s) + lh_font.getlength(lo) + int(26 * s)
        _tri(draw, int(gap_x + tri_r), ly, tri_r, (216, 120, 36), up=True)
        draw.text((gap_x + 2 * tri_r + int(8 * s), ly), bangla.temp_bn(dv.tmax),
                  font=lh_font, fill=(216, 120, 36), anchor="lm")

    # ---- footer ----------------------------------------------------------
    foot_font = _font(int(23 * s), "SemiBold")
    fy = (foot_top + h) // 2
    draw.text((margin, fy), f"তথ্যসূত্র: {report.source}", font=foot_font,
              fill=th.header_sub, anchor="lm")
    draw.text((w - margin, fy), f"হালনাগাদ: {slot}", font=foot_font,
              fill=th.header_sub, anchor="rm")

    return card.convert("RGB"), dot_geom


def build_card(report: WeatherReport, style: CardStyle | None = None) -> Image.Image:
    """Static card (pulse dot shown solid). Used for PNG previews."""
    style = style or CardStyle()
    img, (center, r, color) = _compose(report, style)
    return _draw_pulse_dot(img, center, r, color, 1.0)


def make_frames(report: WeatherReport, style: CardStyle | None, n_frames: int, fps: int = 30):
    """Render `n_frames` with the update dot pulsing; everything else still."""
    style = style or CardStyle()
    base, (center, r, color) = _compose(report, style)
    return [
        _draw_pulse_dot(base, center, r, color, _blink_alpha(i / fps))
        for i in range(n_frames)
    ]


def save_card(report: WeatherReport, out_path: str, style: CardStyle | None = None) -> str:
    img = build_card(report, style)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    from .weather import fetch_report

    save_card(fetch_report(), "output/demo_weather.png")
    print("wrote output/demo_weather.png")
