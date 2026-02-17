"""Load motherboard spec files (Amazon price, PCIe 5.0 slot info)."""

import json
import os
import re

from display_names import shorten_motherboard

MOBO_CACHE_DIR = os.path.join("cache", "motherboards")


def normalize_name(name: str) -> str:
    """Normalize a motherboard name into a filesystem-safe key.

    "ASUS TUF Gaming X870E-PLUS WiFi7" -> "asus_tuf_gaming_x870e_plus_wifi7"
    """
    key = name.lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    key = key.strip("_")
    return key


def load_mobo_spec(raw_name: str) -> dict | None:
    """Look up a motherboard spec file by its raw scraper name.

    Applies display-name shortening, then normalizes to find the JSON file.
    Returns the parsed dict or None if no file exists.
    """
    short = shorten_motherboard(raw_name)
    key = normalize_name(short)
    path = os.path.join(MOBO_CACHE_DIR, f"{key}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_pcie5_x16(slots: int | None, source: str | None) -> str:
    """Format PCIe 5 x16 info for display: '1 (CPU)', '2 (1C+1B)', etc."""
    if slots is None:
        return ""
    if source:
        return f"{slots} ({source})"
    return str(slots)
