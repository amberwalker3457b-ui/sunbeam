"""
widgets/animated_background.py

A slowly drifting color-gradient background. Colors come from the current
theme (derived from cover art, or the default palette). It keeps animating
at all times -- just slower while playback is paused, so the screen never
looks dead, per spec ("moving colors ... even when it is paused").
"""

from __future__ import annotations

from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.clock import Clock
from kivy.properties import ListProperty, BooleanProperty, NumericProperty
import math


class AnimatedBackground(Widget):
    gradient = ListProperty([(18, 18, 20), (28, 20, 48), (20, 18, 30)])
    playing = BooleanProperty(False)
    speed = NumericProperty(1.0)  # multiplier, playing state scales this

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._t = 0.0
        self._blobs = []
        self._n_blobs = 3
        self.bind(size=self._redraw, pos=self._redraw, gradient=self._redraw)
        Clock.schedule_interval(self._tick, 1 / 30)

    def _tick(self, dt):
        # Slow continuous drift at all times; a bit livelier while playing.
        rate = 0.15 if self.playing else 0.05
        self._t += dt * rate * self.speed
        self._redraw()

    def _rgb(self, rgb, alpha=1.0):
        r, g, b = rgb
        return (r / 255, g / 255, b / 255, alpha)

    def _redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        colors = self.gradient or [(18, 18, 20)]
        base = colors[0]

        with self.canvas:
            # Base fill
            Color(*self._rgb(base))
            Rectangle(pos=self.pos, size=self.size)

            # Soft drifting color "blobs" built from the palette, layered
            # with low alpha so they blend into a moving gradient feel
            # without needing a shader.
            n = max(1, len(colors) - 1)
            for i in range(n):
                color = colors[i + 1]
                phase = self._t + i * (2 * math.pi / max(n, 1))
                cx = self.x + self.width * (0.5 + 0.35 * math.sin(phase * 0.7 + i))
                cy = self.y + self.height * (0.5 + 0.35 * math.cos(phase * 0.5 + i * 1.3))
                radius = self.width * 0.55
                Color(*self._rgb(color, alpha=0.35))
                RoundedRectangle(
                    pos=(cx - radius / 2, cy - radius / 2),
                    size=(radius, radius),
                    radius=[radius / 2],
                )

    def set_theme(self, theme):
        """Called by screens when the active track's theme changes."""
        self.gradient = theme.gradient
