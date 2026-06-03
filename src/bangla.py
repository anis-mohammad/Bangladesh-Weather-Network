"""Bangla (Bengali) text helpers: digits, dates, and the daily time-slot label.

Everything user-facing on the weather card is rendered in Bangla, so numbers
and dates need to be converted from Western/ASCII to Bengali numerals and the
Gregorian month names spelled out in Bangla.
"""
from __future__ import annotations

import datetime as _dt

# Western digit -> Bengali digit (০১২৩৪৫৬৭৮৯)
_BN_DIGITS = {ord(str(i)): d for i, d in enumerate("০১২৩৪৫৬৭৮৯")}

# Gregorian months in Bangla (index 1..12)
_BN_MONTHS = [
    "", "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
]

# The four daily posting slots (hour in Asia/Dhaka -> Bangla label).
SLOTS = {10: "সকাল ১০টা", 12: "দুপুর ১২টা", 18: "সন্ধ্যা ৬টা", 22: "রাত ১০টা"}


def to_bn_digits(value) -> str:
    """'34' -> '৩৪', 28.5 -> '২৮.৫'. Accepts str/int/float."""
    return str(value).translate(_BN_DIGITS)


def temp_bn(celsius: float | None) -> str:
    """Round to a whole number and format as Bangla digits with a degree sign."""
    if celsius is None:
        return "—"
    return f"{to_bn_digits(round(celsius))}°"


def bn_date(d: _dt.date | None = None) -> str:
    """'3 June 2026' -> '৩ জুন ২০২৬'."""
    d = d or _dt.date.today()
    return f"{to_bn_digits(d.day)} {_BN_MONTHS[d.month]} {to_bn_digits(d.year)}"


def slot_label(when: _dt.datetime) -> str:
    """Bangla label for the daily slot closest to `when`'s hour (Asia/Dhaka time)."""
    hour = when.hour
    nearest = min(SLOTS, key=lambda h: abs(h - hour))
    return SLOTS[nearest]
