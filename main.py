"""
main.py

SumBeat — a Kivy/KivyMD music app for Android.

Entry point. Wires together:
  - audio_scanner  : find tracks on internal storage
  - player.py      : playback engine
  - theme_manager  : cover-art -> theme, with default fallback
  - storage.py     : favorites persistence

Run on desktop for UI iteration:
    python main.py        (scans ~/Music as a stand-in for device storage)

Package for Android:
    buildozer android debug     (see buildozer.spec)
"""

import os
import sys

# Allow `python main.py` from inside music_app/ as well as from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar

from music_app.player import PlayerEngine
from music_app.storage import FavoritesStore, AppState
from music_app.theme_manager import ThemeCache, DEFAULT_THEME, Theme
from music_app.screens.library_screen import LibraryScreen   # noqa: F401 (registered via kv)
from music_app.screens.player_screen import PlayerScreen       # noqa: F401
from music_app.screens.favorites_screen import FavoritesScreen  # noqa: F401
from music_app.screens.theme_picker_screen import ThemePickerScreen  # noqa: F401


class SumBeatApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"

        self.player = PlayerEngine()
        self.favorites_store = FavoritesStore()
        self.app_state = AppState()
        self.theme_cache = ThemeCache()
        self.library_tracks = []

        kv_path = os.path.join(os.path.dirname(__file__), "sumbeat.kv")
        root = Builder.load_file(kv_path)
        return root

    def on_start(self):
        # Give every screen a back-reference to this app instance.
        sm = self.root
        sm.app_ref = self

        self.player.on_track_changed = self._on_track_changed
        self.player.on_state_changed = self._on_state_changed
        self.player.on_position = self._on_position

        # Respect a previously-pinned preset theme, if any; otherwise default.
        from music_app.named_themes import NAMED_THEMES
        mode = self.app_state.get("theme_mode", "auto")
        name = self.app_state.get("manual_theme_name", "")
        if mode == "manual" and name in NAMED_THEMES:
            self.apply_theme_colors(NAMED_THEMES[name])
        else:
            self.apply_theme_colors(Theme(**DEFAULT_THEME))

    # -- navigation ----------------------------------------------------
    def go_to_favorites(self):
        self.root.current = "favorites"

    def go_to_library(self):
        self.root.current = "library"

    def go_to_theme_picker(self):
        self.root.current = "themes"

    # -- playback entry points from screens -----------------------------
    def play_from_library(self, index: int):
        self.player.set_queue(self.library_tracks, index)
        self.root.current = "player"

    def play_from_track_list(self, tracks, index: int):
        self.player.set_queue(tracks, index)
        self.root.current = "player"

    # -- player engine callbacks -> player screen ------------------------
    def _player_screen(self):
        for screen in self.root.screens:
            if screen.name == "player":
                return screen
        return None

    def _on_track_changed(self, track):
        screen = self._player_screen()
        if screen:
            screen.on_track_changed(track)

    def _on_state_changed(self, playing: bool):
        screen = self._player_screen()
        if screen:
            screen.on_state_changed(playing)

    def _on_position(self, pos, duration):
        screen = self._player_screen()
        if screen:
            screen.on_position(pos, duration)

    # -- theming ---------------------------------------------------------
    def apply_theme_colors(self, theme):
        """Push the derived (or default) theme onto the global KivyMD
        theme + window clear color, so chrome (app bars, dialogs) matches
        the current track's cover art too, not just the player screen."""
        Window.clearcolor = theme.kv(theme.background)
        # KivyMD's dynamic color override; falls back gracefully if the
        # installed KivyMD version doesn't support custom hex injection.
        try:
            r, g, b = theme.accent
            self.theme_cls.primary_palette = "Custom"
            self.theme_cls.primary_hue = "500"
            # KivyMD >= 1.0 supports theme_cls.primary_color (float rgba)
            self.theme_cls.primary_color = theme.kv(theme.accent)
        except Exception:
            pass

    def show_snackbar(self, text: str):
        Snackbar(text=text).open()


if __name__ == "__main__":
    SumBeatApp().run()
