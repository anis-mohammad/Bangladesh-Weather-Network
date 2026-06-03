"""Tiny persistent state for the hashtag rotation cursor (state.json, repo root).

Committed back in CI so the rotation advances across scheduled runs. There is no
posted-history to track here (unlike the old news pipeline) — the weather card is
freshly generated every run — so this only carries the hashtag cursor.
"""
from __future__ import annotations

import json
import os

DEFAULT_STATE = "state.json"


def _load(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as fh:
                data = json.load(fh)
                data.setdefault("hashtag_cursor", 0)
                return data
        except Exception:
            pass
    return {"hashtag_cursor": 0}


def _save(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(state, fh, indent=2)


def peek_hashtags(state_path: str = DEFAULT_STATE) -> tuple[str, int]:
    """Return (rendered hashtag line, cursor) for the next post — does NOT advance."""
    from .hashtags import render

    cursor = _load(state_path).get("hashtag_cursor", 0)
    return render(cursor), cursor


def advance_hashtags(state_path: str, used_cursor: int) -> None:
    """Advance the hashtag cursor by one block after a successful post."""
    from .hashtags import HASHTAGS, PER_POST

    state = _load(state_path)
    state["hashtag_cursor"] = (used_cursor + PER_POST) % len(HASHTAGS)
    _save(state_path, state)
