"""
named_themes.py

Preset themes built from hand-picked images (not tied to any specific
song/album) -- the user chooses one from a picker, or leaves the app on
"Automatic" to keep deriving the theme from whatever track is playing.

Each preset's palette is extracted once at import time via the same
vivid-color pipeline used for cover art, so presets and auto-theming look
and feel consistent with each other.
"""

from __future__ import annotations

import os
from collections import OrderedDict

from .theme_manager import theme_from_cover_bytes, Theme

THEMES_DIR = os.path.join(os.path.dirname(__file__), "assets", "themes")

# (display name, filename) -- order here is the order shown in the picker.
_THEME_SOURCES = [
    ("Fire & Ice", "fire_and_ice.jpg"),
    ("Alone", "alone_lofi.jpg"),
    ("Neon Marble", "neon_marble.jpg"),
    ("Forest Campfire", "forest_campfire.jpg"),
    ("Autumn Canopy", "autumn_canopy.jpg"),
]

AUTO_THEME_LABEL = "Automatic (match cover art)"


def _load() -> "OrderedDict[str, Theme]":
    themes: "OrderedDict[str, Theme]" = OrderedDict()
    for display_name, fname in _THEME_SOURCES:
        path = os.path.join(THEMES_DIR, fname)
        try:
            with open(path, "rb") as f:
                cover_bytes = f.read()
            themes[display_name] = theme_from_cover_bytes(cover_bytes, f"preset:{fname}")
        except Exception:
            # Missing/corrupt asset shouldn't crash the app -- just skip it,
            # it won't show up in the picker.
            continue
    return themes


NAMED_THEMES: "OrderedDict[str, Theme]" = _load()


def get_named_theme(name: str) -> Theme | None:
    return NAMED_THEMES.get(name)


def swatch_hex(theme: Theme) -> str:
    """A single representative hex color for a small picker swatch."""
    r, g, b = theme.accent
    return f"#{r:02x}{g:02x}{b:02x}"
