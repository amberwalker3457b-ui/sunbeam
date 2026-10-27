"""
screens/player_screen.py

The now-playing screen. Owns the AnimatedBackground widget and swaps the
theme whenever the active track changes (driven by cover art color, or
the default theme if there's no art). Background keeps drifting whether
playback is playing or paused.
"""

import io

from kivymd.uix.screen import MDScreen
from kivy.properties import ObjectProperty, StringProperty, NumericProperty, BooleanProperty
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image

from ..named_themes import NAMED_THEMES


class PlayerScreen(MDScreen):
    bg_widget = ObjectProperty(None)
    cover_image = ObjectProperty(None)
    title_label = ObjectProperty(None)
    artist_label = ObjectProperty(None)
    seek_slider = ObjectProperty(None)
    play_pause_icon = StringProperty("play")
    position_text = StringProperty("0:00")
    duration_text = StringProperty("0:00")
    is_playing = BooleanProperty(False)

    def on_track_changed(self, track):
        app = self.manager.app_ref
        self.title_label.text = track.title
        self.artist_label.text = track.artist

        cover_bytes = track.cover_bytes()
        theme = self._resolve_theme(app, track, cover_bytes)
        self._apply_theme(theme)

        if cover_bytes:
            try:
                core_img = CoreImage(io.BytesIO(cover_bytes), ext="png")
                self.cover_image.texture = core_img.texture
            except Exception:
                self.cover_image.source = "assets/default_cover.png"
        else:
            self.cover_image.source = "assets/default_cover.png"

    def _resolve_theme(self, app, track, cover_bytes):
        """Manual preset pinned via the theme picker wins over auto
        per-cover theming; otherwise fall back to cover-art extraction
        (which itself falls back to the default theme with no art)."""
        mode = app.app_state.get("theme_mode", "auto")
        if mode == "manual":
            name = app.app_state.get("manual_theme_name", "")
            theme = NAMED_THEMES.get(name)
            if theme:
                return theme
        return app.theme_cache.get(track.id, cover_bytes)

    def _apply_theme(self, theme):
        self.bg_widget.set_theme(theme)
        app = self.manager.app_ref
        app.apply_theme_colors(theme)

    def on_state_changed(self, playing: bool):
        self.is_playing = playing
        self.play_pause_icon = "pause" if playing else "play"
        self.bg_widget.playing = playing

    def on_position(self, pos: float, duration: float):
        self.position_text = self._fmt(pos)
        self.duration_text = self._fmt(duration)
        if duration > 0 and not self.seek_slider.is_dragging:
            self.seek_slider.value = (pos / duration) * 100

    @staticmethod
    def _fmt(seconds: float) -> str:
        seconds = int(seconds or 0)
        return f"{seconds // 60}:{seconds % 60:02d}"

    # -- UI callbacks ------------------------------------------------
    def toggle_play_pause(self):
        self.manager.app_ref.player.toggle_play_pause()

    def next_track(self):
        self.manager.app_ref.player.next()

    def previous_track(self):
        self.manager.app_ref.player.previous()

    def seek_to_percent(self, percent: float):
        player = self.manager.app_ref.player
        track = player.current_track()
        if track and player._sound and player._sound.length:
            player.seek((percent / 100) * player._sound.length)

    def toggle_favorite(self):
        app = self.manager.app_ref
        track = app.player.current_track()
        if not track:
            return
        new_state = app.favorites_store.toggle(track.id)
        self.ids.fav_icon.icon = "heart" if new_state else "heart-outline"
