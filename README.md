# Bangladesh Weather → Facebook Reel

Fetch temperatures for **all 8 Bangladesh divisions** from
[Meteosource](https://www.meteosource.com/), render a clean 720×900 (4:5)
**Bangla** weather card, turn it into a short MP4, and auto-publish it as a
**Facebook Reel** — locally or on a schedule with GitHub Actions, four times a
day.

```text
Meteosource (8 divisions)  ──▶  Bangla weather card (720×900 PNG)
                           ──▶  short MP4 (H.264 + silent AAC)  ──▶  Facebook Reel
```

Each card lists every division — **ঢাকা, চট্টগ্রাম, রাজশাহী, খুলনা, বরিশাল,
সিলেট, রংপুর, ময়মনসিংহ** — with its **current** temperature (এখন) plus
**today's forecast low and high** (সর্বনিম্ন / সর্বোচ্চ), in Bangla numerals,
colour-coded by heat.

## What's inside

| File | Role |
|------|------|
| [src/weather.py](src/weather.py) | Fetch current temp + condition + today's min/max for all 8 divisions from Meteosource |
| [src/bangla.py](src/bangla.py) | Bangla numerals, dates, and the daily time-slot label (সকাল ১০টা / দুপুর ১২টা / সন্ধ্যা ৬টা / রাত ১০টা) |
| [src/photocard.py](src/photocard.py) | Render the 720×900 light-theme Bangla weather card with Pillow (Noto Sans Bengali via raqm; BWN logo + Meteocons icons) |
| [tools/render_icons.py](tools/render_icons.py) | Build-time: rasterise the weather icons from Meteocons SVGs to `assets/icons/*.png` (not needed at runtime) |
| [src/video.py](src/video.py) | Card → short MP4 with a pulsing "live update" dot, via `ffmpeg` |
| [src/hashtags.py](src/hashtags.py) | Weather / Bangladesh hashtags, used a rotating block per post |
| [src/store.py](src/store.py) | Tiny `state.json` store for the hashtag-rotation cursor |
| [src/facebook.py](src/facebook.py) | Publish a Reel through the Graph API resumable-upload flow |
| [main.py](main.py) | CLI that wires the whole pipeline together |
| [.github/workflows/post-weather.yml](.github/workflows/post-weather.yml) | Scheduled (4×/day) / manual auto-posting |

## Data source & accuracy

Temperatures come from **[Meteosource](https://www.meteosource.com/)** via its
free `point` endpoint — one request per divisional HQ city (8 per run). The card
uses `current.temperature` and `current.icon` for the condition, plus the day's
`temperature_min` / `temperature_max`. Each division is keyed to its divisional
HQ city (Dhaka, Chattogram, Rajshahi, Khulna, Barishal, Sylhet, Rangpur,
Mymensingh) — edit the coordinates in [src/weather.py](src/weather.py) to track
different points.

Meteosource is a multi-model forecast provider, not the official BMD station
network, so treat the figures as accurate-to-a-degree-or-two model estimates
rather than exact readings. The free tier allows **400 calls/day, 10/min** —
well above this project's 8 divisions × 4 posts/day = 32 calls/day — but is for
**non-commercial** use and requires an attribution backlink, which the pipeline
adds to every caption automatically.

## Requirements

- Python 3.12
- `ffmpeg` on PATH (`brew install ffmpeg`)
- Pillow built **with raqm** (the official pip wheels are — needed so Bangla
  conjuncts/vowel-reordering like *সিলেট* render correctly)

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env          # then fill in the keys below
```

Fill `.env` with:

- `METEOSOURCE_API_KEY` — free key from [meteosource.com](https://www.meteosource.com/) (the weather data source)
- `FB_PAGE_ID` + `FB_PAGE_ACCESS_TOKEN` — for publishing Reels (see below)

Sanity-check Bangla shaping support:

```bash
.venv/bin/python -c "from PIL import features; print('raqm:', features.check('raqm'))"
```

## Usage

Build the card + video **without** posting (great for previewing):

```bash
.venv/bin/python main.py --no-post
```

Outputs land in `output/` as `YYYYMMDD-HHMM-bd-weather.png` and `.mp4`.

Build **and publish** a Reel in one go:

```bash
.venv/bin/python main.py
```

Two-step (build now, publish the exact staged asset later — what the workflow
does):

```bash
.venv/bin/python main.py --no-post
.venv/bin/python main.py --publish
```

Handy flags:

| Flag | Effect |
|------|--------|
| `--brand "..."` | Title shown on the card (default: বাংলাদেশ আবহাওয়া) |
| `--caption "..."` | Extra text appended to the Reel caption |
| `--duration 5` | Video length in seconds (default 4) |
| `--no-post` | Build assets only |

## Getting Facebook credentials

You need a **Facebook Page** and a **long-lived Page access token** with the
scopes `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`.

1. Create an app at [developers.facebook.com](https://developers.facebook.com/).
2. In **Graph API Explorer**, select your app + Page, request the scopes above,
   and generate a User token.
3. Exchange it for a long-lived token, then get the **Page** token (the helper
   [get_token.py](get_token.py) automates this):
   ```bash
   .venv/bin/python get_token.py SHORT_USER_TOKEN APP_ID APP_SECRET
   ```
4. Put the Page `id` and `access_token` into `.env`.

> Page tokens derived from a long-lived user token don't expire as long as the
> user stays logged in and the app stays active — good for automation.

## Automating with GitHub Actions

The workflow builds and posts a weather Reel four times a day. After pushing
this project to your own repo:

1. **Repo → Settings → Secrets and variables → Actions**
   - Secrets: `METEOSOURCE_API_KEY`, `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`
2. The schedule in [post-weather.yml](.github/workflows/post-weather.yml) runs
   at **10:00, 12:00, 18:00 and 22:00 Bangladesh time** (cron is UTC, so
   04:00/06:00/12:00/16:00 UTC). Adjust to taste.
3. Trigger manually from the **Actions** tab — tick `no_post` to dry-run
   (assets are uploaded as a build artifact, nothing is published).

> The hashtag-rotation cursor (`state.json`) is committed back after each run so
> captions aren't byte-identical run to run. The workflow needs `contents:
> write` permission (already set) to push that commit.

## Notes & limits

- Reels require a video ≥ 3s with an audio stream — we add a silent AAC track.
- Meteosource's free tier is **non-commercial** and requires attribution (added
  to the caption). For a business/monetized page, move to a paid plan.
- Forecast min/max can shift slightly through the day as models update; that's
  expected — the card always reflects the latest fetch.
