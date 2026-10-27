"""
widgets/seek_slider.py

A slider that:
  1) tracks `is_dragging` so the position poller doesn't yank the handle
     while the user is touching it, and
  2) fires a clean `on_user_seek` event (with the released value) instead
     of the screen having to peek into the slider's touch internals.
"""

from kivymd.uix.slider import MDSlider
from kivy.properties import BooleanProperty


class SeekSlider(MDSlider):
    is_dragging = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.register_event_type("on_user_seek")
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.is_dragging = True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        was_dragging = self.is_dragging
        result = super().on_touch_up(touch)
        if was_dragging:
            self.is_dragging = False
            self.dispatch("on_user_seek", self.value)
        return result

    def on_user_seek(self, value):
        pass
