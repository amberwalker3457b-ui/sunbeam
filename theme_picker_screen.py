"""
screens/theme_picker_screen.py

Lets the user pick one of the named preset themes (built from their
uploaded images) or go back to "Automatic", where the theme follows
whatever track's cover art is currently playing.

Selection is persisted via AppState so it survives app restarts, and
applied immediately (including to whatever's on screen right now).
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivy.properties import ObjectProperty

from ..named_themes import NAMED_THEMES, AUTO_THEME_LABEL
from ..theme_manager import DEFAULT_THEME, Theme


class ThemeRow(OneLineAvatarIconListItem):
    pass


class ThemePickerScreen(MDScreen):
    list_container = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        app = self.manager.app_ref
        self.list_container.clear_widgets()

        current = app.app_state.get("theme_mode", "auto")
        current_name = app.app_state.get("manual_theme_name", "")

        # "Automatic" option first.
        auto_row = ThemeRow(
            text=AUTO_THEME_LABEL,
            secondary_text="Changes with every track's cover art",
        )
        icon_name = "check-circle" if current == "auto" else "circle-outline"
        auto_row.add_widget(IconLeftWidget(icon=icon_name))
        auto_row.bind(on_release=lambda w: self._select_auto())
        self.list_container.add_widget(auto_row)

        for name, theme in NAMED_THEMES.items():
            is_selected = (current == "manual" and current_name == name)
            row = ThemeRow(text=name)
            icon_name = "check-circle" if is_selected else "circle-outline"
            icon = IconLeftWidget(icon=icon_name)
            r, g, b = theme.accent
            icon.theme_text_color = "Custom"
            icon.text_color = (r / 255, g / 255, b / 255, 1)
            row.add_widget(icon)
            row.bind(on_release=lambda w, n=name: self._select_named(n))
            self.list_container.add_widget(row)

    def _select_auto(self):
        app = self.manager.app_ref
        app.app_state.set("theme_mode", "auto")
        # Re-apply using whatever's currently playing, or default if nothing is.
        track = app.player.current_track()
        if track:
            cover_bytes = track.cover_bytes()
            theme = app.theme_cache.get(track.id, cover_bytes)
        else:
            theme = Theme(**DEFAULT_THEME)
        app.apply_theme_colors(theme)
        self.refresh()

    def _select_named(self, name: str):
        app = self.manager.app_ref
        app.app_state.set("theme_mode", "manual")
        app.app_state.set("manual_theme_name", name)
        theme = NAMED_THEMES[name]
        app.apply_theme_colors(theme)
        # If the player screen is visible/has a track, push the theme into
        # its animated background too, not just global chrome colors.
        for screen in self.manager.screens:
            if screen.name == "player" and hasattr(screen, "bg_widget"):
                screen.bg_widget.set_theme(theme)
        self.refresh()
