"""
theme_manager.py

Builds a UI theme from a song's embedded album art.

Pipeline:
    cover bytes -> Pillow image -> shrink to a few px -> quantize to find
    the most common color -> derive a small palette (bg / surface / accent /
    text) that stays readable -> cache per-track so we don't recompute.

If a track has no embedded art, `DEFAULT_THEME` is used untouched, per spec.
"""

from __future__ import annotations

import colorsys
import io
import os
from dataclasses import dataclass, asdict
from typing import Optional, Tuple

from PIL import Image

RGB = Tuple[int, int, int]


# ---------------------------------------------------------------------------
# Default theme (used whenever a track has no cover art)
# ---------------------------------------------------------------------------

DEFAULT_THEME = {
    "name": "default",
    "background": (18, 18, 20),
    "surface": (28, 28, 32),
    "accent": (124, 92, 255),      # soft violet, matches a generic "music app" feel
    "accent_dim": (90, 68, 180),
    "text_primary": (240, 240, 245),
    "text_secondary": (160, 160, 170),
    "gradient": [(18, 18, 20), (28, 20, 48), (20, 18, 30)],
}


@dataclass
class Theme:
    name: str
    background: RGB
    surface: RGB
    accent: RGB
    accent_dim: RGB
    text_primary: RGB
    text_secondary: RGB
    gradient: list  # list[RGB] used by the animated background widget

    def as_dict(self):
        return asdict(self)

    # Kivy wants 0-1 floats with alpha; convenience converters below.
    def kv(self, rgb: RGB, alpha: float = 1.0):
        r, g, b = rgb
        return (r / 255, g / 255, b / 255, alpha)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _relative_luminance(rgb: RGB) -> float:
    r, g, b = [c / 255 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ensure_contrast(bg: RGB, fg: RGB, min_diff: float = 0.45) -> RGB:
    """If fg doesn't contrast enough against bg, push fg toward white/black."""
    bg_l = _relative_luminance(bg)
    fg_l = _relative_luminance(fg)
    if abs(bg_l - fg_l) >= min_diff:
        return fg
    target = (255, 255, 255) if bg_l < 0.5 else (20, 20, 20)
    return target


def _saturation(rgb: RGB) -> float:
    r, g, b = [c / 255 for c in rgb]
    _, _, s = colorsys.rgb_to_hls(r, g, b)
    return s


def _color_distance(a: RGB, b: RGB) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _palette_with_counts(image: Image.Image, n_colors: int = 12):
    """Quantize down to n_colors and return [(count, (r,g,b)), ...] sorted
    by frequency, most common first."""
    small = image.convert("RGB").resize((64, 64))
    quantized = small.quantize(colors=n_colors, method=Image.FASTOCTREE)
    palette = quantized.getpalette()
    color_counts = quantized.getcolors() or []
    out = []
    for count, idx in color_counts:
        r, g, b = palette[idx * 3: idx * 3 + 3]
        out.append((count, (r, g, b)))
    out.sort(reverse=True, key=lambda c: c[0])
    return out


def _dominant_color(image: Image.Image) -> RGB:
    """Picks a representative color that's actually *vivid*, not just the
    most frequent pixel -- a busy photo's most common color is usually
    near-black shadow, which makes a flat, characterless theme. We score
    each quantized color by frequency weighted toward saturation, so a
    smaller patch of vibrant orange/blue/pink can win over a sea of near-
    black background."""
    counts = _palette_with_counts(image, n_colors=12)
    if not counts:
        return (120, 120, 120)

    total = sum(c for c, _ in counts) or 1

    def score(count, rgb):
        freq = count / total
        sat = _saturation(rgb)
        r, g, b = [c / 255 for c in rgb]
        _, l, _ = colorsys.rgb_to_hls(r, g, b)
        # Reward saturated, mid-brightness colors; frequency still matters
        # but no longer dominates over a vivid accent color.
        vividness = sat * (1 - abs(l - 0.5) * 0.6)
        return freq * 0.4 + vividness * 0.6

    best = max(counts, key=lambda c: score(*c))
    return best[1]


def _vivid_palette(image: Image.Image, n: int = 3, min_distance: float = 60.0) -> list:
    """Top-n distinct, vivid colors for building a multi-stop gradient.
    Skips colors too close to ones already picked so the gradient doesn't
    end up as three near-identical shades."""
    counts = _palette_with_counts(image, n_colors=12)
    if not counts:
        return [(60, 60, 60)] * n

    total = sum(c for c, _ in counts) or 1

    def score(count, rgb):
        freq = count / total
        sat = _saturation(rgb)
        return freq * 0.35 + sat * 0.65

    ranked = sorted(counts, key=lambda c: score(*c), reverse=True)

    picked: list = []
    for _count, rgb in ranked:
        if all(_color_distance(rgb, p) >= min_distance for p in picked):
            picked.append(rgb)
        if len(picked) == n:
            break

    # Not enough distinct colors (e.g. near-monochrome image) -> pad by
    # relaxing the distance requirement.
    if len(picked) < n:
        for _count, rgb in ranked:
            if rgb not in picked:
                picked.append(rgb)
            if len(picked) == n:
                break

    return picked[:n]


def _shift(rgb: RGB, dl: float = 0.0, ds: float = 0.0) -> RGB:
    """Shift a color's lightness/saturation in HLS space."""
    r, g, b = [c / 255 for c in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = _clamp(l + dl)
    s = _clamp(s + ds)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return (int(r2 * 255), int(g2 * 255), int(b2 * 255))


def theme_from_cover_bytes(cover_bytes: Optional[bytes], track_id: str) -> Theme:
    """Build a Theme from raw embedded-art bytes. None/invalid -> default."""
    if not cover_bytes:
        return Theme(**DEFAULT_THEME)

    try:
        image = Image.open(io.BytesIO(cover_bytes))
        dominant = _dominant_color(image)
    except Exception:
        return Theme(**DEFAULT_THEME)

    # Background: darken the dominant color so text stays legible.
    background = _shift(dominant, dl=-0.35, ds=-0.10)
    surface = _shift(dominant, dl=-0.25, ds=-0.05)
    accent = _shift(dominant, dl=0.05, ds=0.15)
    accent_dim = _shift(dominant, dl=-0.10, ds=0.05)

    text_primary = _ensure_contrast(background, (245, 245, 248))
    text_secondary = _ensure_contrast(background, (190, 190, 198), min_diff=0.3)

    vivid = _vivid_palette(image, n=3)
    gradient = [background] + [_shift(c, dl=-0.08) for c in vivid]

    return Theme(
        name=f"cover:{track_id}",
        background=background,
        surface=surface,
        accent=accent,
        accent_dim=accent_dim,
        text_primary=text_primary,
        text_secondary=text_secondary,
        gradient=gradient,
    )


class ThemeCache:
    """In-memory cache so we don't re-decode/re-quantize art on every screen
    change for the same track."""

    def __init__(self):
        self._cache: dict[str, Theme] = {}

    def get(self, track_id: str, cover_bytes: Optional[bytes]) -> Theme:
        if track_id in self._cache:
            return self._cache[track_id]
        theme = theme_from_cover_bytes(cover_bytes, track_id)
        self._cache[track_id] = theme
        return theme

    def clear(self):
        self._cache.clear()
