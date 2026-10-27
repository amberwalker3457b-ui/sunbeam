"""
screens/library_screen.py

Shows every track found on internal storage. Tapping a row plays it
(queueing the whole visible list so next/prev work); the heart icon
toggles favorite status without leaving the screen.
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget, IconRightWidget
from kivy.properties import ObjectProperty
from kivy.clock import Clock

from ..audio_scanner import scan_all_audio, request_storage_permission


class TrackRow(OneLineAvatarIconListItem):
    pass


class LibraryScreen(MDScreen):
    list_container = ObjectProperty(None)

    def on_pre_enter(self, *args):
        if not self.list_container.children:
            self.load_tracks()

    def load_tracks(self):
        def _after_permission(granted):
            if not granted:
                self._show_permission_denied()
                return
            Clock.schedule_once(lambda dt: self._populate(), 0)

        request_storage_permission(on_result=_after_permission)

    def _show_permission_denied(self):
        app = self.manager.app_ref
        app.show_snackbar("Storage permission is needed to find your music.")

    def _populate(self):
        app = self.manager.app_ref
        tracks = scan_all_audio()
        app.library_tracks = tracks
        self.list_container.clear_widgets()

        if not tracks:
            return

        for i, track in enumerate(tracks):
            is_fav = app.favorites_store.is_favorite(track.id)
            row = TrackRow(text=f"{track.title}", secondary_text=track.artist)
            row.add_widget(IconLeftWidget(icon="music-note"))
            heart = IconRightWidget(
                icon="heart" if is_fav else "heart-outline",
            )
            heart.track_id = track.id
            heart.bind(on_release=lambda w, idx=i: self._toggle_favorite(w))
            row.add_widget(heart)
            row.bind(on_release=lambda w, idx=i: app.play_from_library(idx))
            self.list_container.add_widget(row)

    def _toggle_favorite(self, heart_widget):
        app = self.manager.app_ref
        new_state = app.favorites_store.toggle(heart_widget.track_id)
        heart_widget.icon = "heart" if new_state else "heart-outline"
