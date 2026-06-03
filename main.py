"""Bangladesh weather -> Bangla photocard -> short video -> Facebook Reel.

Fetches current + today's min/max temperatures for all 8 divisions from
Meteosource, renders a Bangla weather card, turns it into a short MP4, and
publishes it as a Facebook Reel.

Examples:
  # Build the card + video only (great for previewing), do not post:
  python main.py --no-post

  # Build and publish in one go:
  python main.py

  # Two-step (build now, publish the exact staged asset later):
  python main.py --no-post
  python main.py --publish

Credentials for posting come from environment / .env:
  FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from dotenv import load_dotenv

from src import bangla, store
from src.photocard import CardStyle, make_frames, save_card
from src.video import encode_frames
from src.weather import WeatherReport, fetch_report


def build_caption(report: WeatherReport, extra: str | None, hashtags: str | None) -> str:
    """Bangla caption: title + a hottest/coolest one-liner + optional extra + tags."""
    slot = bangla.slot_label(report.fetched_at)
    date_str = bangla.bn_date(report.fetched_at.date())
    valid = [d for d in report.divisions if d.current is not None]
    parts = [f"বাংলাদেশের ৮ বিভাগের আবহাওয়া • {date_str} ({slot})"]
    if valid:
        hot = max(valid, key=lambda d: d.current)
        cool = min(valid, key=lambda d: d.current)
        parts.append(
            f"🔥 সর্বোচ্চ: {hot.name_bn} {bangla.temp_bn(hot.current)}   "
            f"❄️ সর্বনিম্ন: {cool.name_bn} {bangla.temp_bn(cool.current)}"
        )
    if extra:
        parts.append(extra)
    caption = "\n".join(parts)
    if hashtags:
        caption += f"\n\n{hashtags}"
    return caption


def build_source_comment(report: WeatherReport) -> str:
    """Attribution posted as the first comment (with the backlink), not in the caption."""
    return f"তথ্যসূত্র: {report.source} — {report.source_url}"


def _save_staged(path, video_path, card_path, caption, source_comment,
                 hashtag_cursor, state_path) -> None:
    payload = {
        "video_path": video_path,
        "card_path": card_path,
        "caption": caption,
        "source_comment": source_comment,   # posted as the first comment
        "hashtag_cursor": hashtag_cursor,   # block used; advanced on publish
        "state_path": state_path,
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)


def _publish_staged(staged_path: str) -> int:
    if not os.path.exists(staged_path):
        print(f"✗ Nothing staged ({staged_path}). Run the build step first.")
        return 1
    with open(staged_path) as fh:
        staged = json.load(fh)
    video_path = staged["video_path"]
    if not os.path.exists(video_path):
        print(f"✗ Staged video missing: {video_path}")
        return 1

    print("→ Publishing staged weather Reel…")
    from src.facebook import FacebookError, comment, post_reel  # late import: creds only here

    result = post_reel(video_path, description=staged["caption"])
    print(f"✓ Published. video_id={result.get('video_id')}  post_id={result.get('post_id')}")

    # source attribution (with backlink) as the first comment — kept out of the caption
    src_comment = staged.get("source_comment", "")
    if src_comment:
        posted = False
        for obj_id in (result.get("video_id"), result.get("post_id")):
            if not obj_id:
                continue
            try:
                cres = comment(obj_id, src_comment)
                print(f"✓ Source comment posted (id={cres.get('id')}).")
                posted = True
                break
            except FacebookError:
                continue
        if not posted:
            print("⚠ Could not auto-post the source comment. Add it manually:")
            print("  " + src_comment)

    # advance the hashtag block so the next post uses the next set
    if staged.get("hashtag_cursor") is not None and staged.get("state_path"):
        store.advance_hashtags(staged["state_path"], staged["hashtag_cursor"])
    os.remove(staged_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    p = argparse.ArgumentParser(description="Bangladesh weather -> Facebook Reel pipeline")
    p.add_argument("--publish", action="store_true", help="publish the previously staged Reel")
    p.add_argument("--state", default="state.json", help="hashtag-rotation state file")
    p.add_argument("--staged", default="staged.json", help="staged-Reel file (build→publish)")
    p.add_argument("--brand", help="title shown on the card (default: বাংলাদেশ আবহাওয়া)")
    p.add_argument("--duration", type=float, default=4.0, help="video length in seconds")
    p.add_argument("--no-post", action="store_true", help="build + stage but do not publish")
    p.add_argument("--caption", help="extra text appended to the Reel caption")
    p.add_argument("--outdir", default="output", help="output directory")
    args = p.parse_args(argv)

    # publish mode: post the exact staged Reel (what was previewed)
    if args.publish:
        return _publish_staged(args.staged)

    # 1. fetch accurate weather for all 8 divisions
    print("→ Fetching weather for all 8 divisions (Meteosource)…")
    report = fetch_report()
    for d in report.divisions:
        print(f"  {d.name_en:12s} now={d.current}  low={d.tmin}  high={d.tmax}  {d.condition}")

    base = f"{date.today():%Y%m%d}-{report.fetched_at:%H%M}-bd-weather"
    card_path = f"{args.outdir}/{base}.png"
    video_path = f"{args.outdir}/{base}.mp4"

    # 2. photocard
    print("→ Building Bangla weather card…")
    style = CardStyle(brand=args.brand) if args.brand else CardStyle()
    save_card(report, card_path, style)
    print(f"  {card_path}")

    # 3. video — card with the pulsing "live update" dot
    print("→ Rendering video…")
    fps = 30
    n_frames = max(1, int(round(args.duration * fps)))
    frames = make_frames(report, style, n_frames, fps=fps)
    encode_frames(frames, video_path, fps=fps, duration=args.duration)
    print(f"  {video_path}")

    # 4. stage the exact assets so --publish posts precisely this card
    hashtag_line, hashtag_cursor = store.peek_hashtags(args.state)
    caption = build_caption(report, args.caption, hashtag_line)
    source_comment = build_source_comment(report)
    print(f"  hashtags: {hashtag_line}")
    _save_staged(args.staged, video_path, card_path, caption, source_comment,
                 hashtag_cursor, args.state)

    if args.no_post:
        print(f"✓ Staged (not posted). Review {card_path}, then run:  python main.py --publish")
        return 0
    return _publish_staged(args.staged)


if __name__ == "__main__":
    sys.exit(main())
