"""
screens/favorites_screen.py

Mirrors LibraryScreen but filtered to tracks the user has starred.
Un-favoriting here removes it from the list immediately.
"""

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget, IconRightWidget
from kivy.properties import ObjectProperty


class FavRow(OneLineAvatarIconListItem):
    pass


class FavoritesScreen(MDScreen):
    list_container = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        app = self.manager.app_ref
        fav_ids = set(app.favorites_store.all_ids())
        fav_tracks = [t for t in app.library_tracks if t.id in fav_ids]

        self.list_container.clear_widgets()
        if not fav_tracks:
            return

        for i, track in enumerate(fav_tracks):
            row = FavRow(text=track.title, secondary_text=track.artist)
            row.add_widget(IconLeftWidget(icon="music-note"))
            heart = IconRightWidget(icon="heart")
            heart.track_id = track.id
            heart.bind(on_release=lambda w: self._unfavorite(w))
            row.add_widget(heart)
            row.bind(
                on_release=lambda w, tr=track: app.play_from_track_list(fav_tracks, fav_tracks.index(tr))
            )
            self.list_container.add_widget(row)

    def _unfavorite(self, heart_widget):
        app = self.manager.app_ref
        app.favorites_store.toggle(heart_widget.track_id)
        self.refresh()
