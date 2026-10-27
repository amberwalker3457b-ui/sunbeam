"""
audio_scanner.py

Finds every playable audio file on the device's internal storage and reads
its tags + embedded cover art.

Two code paths:
  * On Android: queries MediaStore.Audio.Media via pyjnius, which is the
    correct/fast way to enumerate music without walking the whole
    filesystem by hand (and it respects scoped storage).
  * Off Android (desktop dev/testing): falls back to walking a music
    folder on disk, so you can build/test the UI without a phone.

Both paths funnel into the same `Track` objects so the rest of the app
never has to know which platform it's on.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from mutagen import File as MutagenFile

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".opus", ".aac"}

try:
    from android.permissions import request_permissions, Permission, check_permission  # noqa
    from jnius import autoclass  # noqa
    ON_ANDROID = True
except Exception:
    ON_ANDROID = False


@dataclass
class Track:
    id: str                 # stable unique id (content URI on Android, path elsewhere)
    path: str                # playable URI/path
    title: str
    artist: str
    album: str
    duration_ms: int
    has_cover: bool

    def cover_bytes(self) -> Optional[bytes]:
        """Lazy-load embedded cover art bytes (not cached here; ThemeCache
        upstream handles caching the derived theme, not the raw bytes)."""
        if not self.has_cover:
            return None
        try:
            audio = MutagenFile(self.path)
            return _extract_cover_bytes(audio)
        except Exception:
            return None


def _extract_cover_bytes(audio) -> Optional[bytes]:
    if audio is None:
        return None
    # MP3 (ID3 APIC frames)
    tags = getattr(audio, "tags", None)
    if tags:
        for key in tags.keys():
            if key.startswith("APIC"):
                return tags[key].data
    # FLAC / some others expose .pictures
    pictures = getattr(audio, "pictures", None)
    if pictures:
        return pictures[0].data
    # MP4/M4A cover is under tags["covr"]
    if tags and "covr" in tags:
        covr = tags["covr"]
        if covr:
            return bytes(covr[0])
    return None


def request_storage_permission(on_result=None):
    """Request the right permission for the device's Android version.
    Android 13+ (API 33+) uses READ_MEDIA_AUDIO; older uses
    READ_EXTERNAL_STORAGE. No-op off Android."""
    if not ON_ANDROID:
        if on_result:
            on_result(True)
        return

    perms = [Permission.READ_MEDIA_AUDIO] if hasattr(Permission, "READ_MEDIA_AUDIO") \
        else [Permission.READ_EXTERNAL_STORAGE]

    def _callback(permissions, grants):
        if on_result:
            on_result(all(grants))

    request_permissions(perms, _callback)


def scan_android_mediastore() -> List[Track]:
    """Query MediaStore for every audio track on internal (and mounted
    external) storage."""
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    MediaStore = autoclass("android.provider.MediaStore$Audio$Media")
    context = PythonActivity.mActivity.getApplicationContext()
    resolver = context.getContentResolver()

    uri = MediaStore.EXTERNAL_CONTENT_URI
    projection = autoclass("java.lang.String")
    columns = [
        "_id", "_data", "title", "artist", "album", "duration", "is_music",
    ]
    String = autoclass("java.lang.String")
    columns_arr = [String(c) for c in columns]

    cursor = resolver.query(uri, columns_arr, None, None, None)
    tracks: List[Track] = []
    if cursor is None:
        return tracks

    try:
        idx = {name: cursor.getColumnIndexOrThrow(name) for name in columns}
        while cursor.moveToNext():
            is_music = cursor.getInt(idx["is_music"])
            if not is_music:
                continue
            track_id = str(cursor.getLong(idx["_id"]))
            data_path = cursor.getString(idx["_data"])
            title = cursor.getString(idx["title"]) or os.path.basename(data_path or "Unknown")
            artist = cursor.getString(idx["artist"]) or "Unknown Artist"
            album = cursor.getString(idx["album"]) or "Unknown Album"
            duration = cursor.getLong(idx["duration"]) or 0

            has_cover = False
            try:
                audio = MutagenFile(data_path)
                has_cover = _extract_cover_bytes(audio) is not None
            except Exception:
                pass

            tracks.append(Track(
                id=track_id,
                path=data_path,
                title=title,
                artist=artist,
                album=album,
                duration_ms=int(duration),
                has_cover=has_cover,
            ))
    finally:
        cursor.close()

    return tracks


def scan_desktop_folder(music_dir: Optional[str] = None) -> List[Track]:
    """Desktop fallback for development/testing without a device.
    Defaults to ~/Music."""
    music_dir = music_dir or os.path.expanduser("~/Music")
    tracks: List[Track] = []
    if not os.path.isdir(music_dir):
        return tracks

    for root, _dirs, files in os.walk(music_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in AUDIO_EXTENSIONS:
                continue
            full_path = os.path.join(root, fname)
            title, artist, album, duration_ms, has_cover = fname, "Unknown Artist", "Unknown Album", 0, False
            try:
                audio = MutagenFile(full_path)
                if audio is not None:
                    tags = audio.tags or {}
                    title = str(tags.get("TIT2", title)) if tags.get("TIT2") else title
                    artist = str(tags.get("TPE1", artist)) if tags.get("TPE1") else artist
                    album = str(tags.get("TALB", album)) if tags.get("TALB") else album
                    if getattr(audio, "info", None) and getattr(audio.info, "length", None):
                        duration_ms = int(audio.info.length * 1000)
                    has_cover = _extract_cover_bytes(audio) is not None
            except Exception:
                pass

            tracks.append(Track(
                id=full_path,
                path=full_path,
                title=title,
                artist=artist,
                album=album,
                duration_ms=duration_ms,
                has_cover=has_cover,
            ))

    return tracks


def scan_all_audio() -> List[Track]:
    """Entry point the app actually calls."""
    if ON_ANDROID:
        return scan_android_mediastore()
    return scan_desktop_folder()
