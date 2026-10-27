"""
player.py

Thin playback engine. Uses Kivy's SoundLoader (backed by ffpyplayer/gstreamer
depending on platform) so the same code path works on Android and desktop.
Exposes simple play/pause/seek/next/prev + a position callback the UI
polls to update the seek bar.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from kivy.core.audio import SoundLoader
from kivy.clock import Clock

from .audio_scanner import Track


class PlayerEngine:
    def __init__(self):
        self.queue: List[Track] = []
        self.index: int = -1
        self._sound = None
        self.on_track_changed: Optional[Callable[[Track], None]] = None
        self.on_state_changed: Optional[Callable[[bool], None]] = None  # bool = playing
        self.on_position: Optional[Callable[[float, float], None]] = None  # pos, duration
        Clock.schedule_interval(self._poll_position, 0.25)

    # -- queue management ---------------------------------------------
    def set_queue(self, tracks: List[Track], start_index: int = 0):
        self.queue = tracks
        self.play_index(start_index)

    def play_index(self, idx: int):
        if not self.queue or not (0 <= idx < len(self.queue)):
            return
        self._stop_current()
        self.index = idx
        track = self.queue[idx]
        self._sound = SoundLoader.load(track.path)
        if self._sound:
            self._sound.bind(on_stop=self._on_sound_finished)
            self._sound.play()
        if self.on_track_changed:
            self.on_track_changed(track)
        if self.on_state_changed:
            self.on_state_changed(True)

    def current_track(self) -> Optional[Track]:
        if 0 <= self.index < len(self.queue):
            return self.queue[self.index]
        return None

    # -- transport -------------------------------------------------------
    def toggle_play_pause(self):
        if not self._sound:
            return
        if self._sound.state == "play":
            self._sound.stop()
            if self.on_state_changed:
                self.on_state_changed(False)
        else:
            self._sound.play()
            if self.on_state_changed:
                self.on_state_changed(True)

    def next(self):
        if not self.queue:
            return
        self.play_index((self.index + 1) % len(self.queue))

    def previous(self):
        if not self.queue:
            return
        self.play_index((self.index - 1) % len(self.queue))

    def seek(self, position_seconds: float):
        if self._sound:
            self._sound.seek(position_seconds)

    def is_playing(self) -> bool:
        return bool(self._sound and self._sound.state == "play")

    # -- internals ---------------------------------------------------
    def _stop_current(self):
        if self._sound:
            self._sound.unbind(on_stop=self._on_sound_finished)
            self._sound.stop()
            self._sound.unload()
            self._sound = None

    def _on_sound_finished(self, *args):
        # Auto-advance when a track ends naturally.
        self.next()

    def _poll_position(self, dt):
        if self._sound and self.on_position:
            pos = self._sound.get_pos() or 0.0
            duration = self._sound.length or 0.0
            self.on_position(pos, duration)
