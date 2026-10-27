# SumBeat

A Python/Kivy Android music app: scans internal-storage audio, themes itself
from each track's cover art (falling back to a default theme when a track
has none), animates a moving color background behind the player, and lets
you favorite tracks.

## Why Kivy

"Python on Android" needs a UI toolkit to produce an installable `.apk` —
there's no bare-Python path to a native Android app. Kivy + KivyMD is the
standard, actively-maintained choice, packaged with **Buildozer**.

## Project layout

```
sumbeat/
├── buildozer.spec              # Android packaging config (permissions, deps)
├── requirements.txt            # desktop dev dependencies
└── music_app/
    ├── main.py                 # app entry point, wires everything together
    ├── sumbeat.kv               # all screen layouts
    ├── player.py                # playback engine (play/pause/seek/next/prev)
    ├── audio_scanner.py         # MediaStore scan (Android) + folder scan (desktop)
    ├── theme_manager.py         # cover-art -> color theme, default fallback
    ├── storage.py                # SQLite: favorites + app state
    ├── widgets/
    │   ├── animated_background.py  # moving gradient, theme-driven
    │   └── seek_slider.py          # drag-safe seek bar
    ├── screens/
    │   ├── library_screen.py
    │   ├── player_screen.py
    │   └── favorites_screen.py
    └── assets/
        └── default_cover.png    # shown when a track has no embedded art
```

## Run on desktop (fast iteration loop)

```bash
pip install -r requirements.txt
python music_app/main.py
```

On desktop, the scanner walks `~/Music` instead of querying Android's
MediaStore, so you can build/test the UI without a phone. Drop a few mp3s
with embedded cover art in there to see the theming react.

## Build the actual Android APK

```bash
pip install buildozer
buildozer -v android debug
```

The first build downloads the Android SDK/NDK and will take a while.
The resulting APK lands in `bin/`. Install it with:

```bash
buildozer android deploy run logcat
```

`buildozer.spec` already declares `READ_MEDIA_AUDIO` (Android 13+) and
`READ_EXTERNAL_STORAGE` (older versions) so the app can see all audio on
internal storage; the app requests the permission at runtime on first
launch (handled in `audio_scanner.request_storage_permission`).

## How the theming works

1. When a track starts playing, `audio_scanner.Track.cover_bytes()` pulls
   the embedded album art (ID3 APIC for mp3, FLAC pictures, or MP4 `covr`)
   via `mutagen`.
2. `theme_manager.theme_from_cover_bytes()` quantizes the image down to its
   dominant color and derives a full palette (background/surface/accent/
   text) from it, adjusting lightness so text stays readable.
3. If there's no cover art, `DEFAULT_THEME` is used unchanged — nothing
   is guessed.
4. `PlayerScreen.on_track_changed` applies the theme to the
   `AnimatedBackground` (the moving gradient) and to the app-wide
   KivyMD theme (`MDApp.apply_theme_colors`), so app bars match too.
5. `AnimatedBackground` redraws on a 30fps clock tick regardless of
   play state — just a bit faster while a track is actively playing —
   so the screen keeps moving even when paused, as requested.

## Preset themes (from your uploaded images)

`music_app/assets/themes/` now holds 5 of your images, each turned into a
full theme via `named_themes.py`:

| Preset | Source image | Vibe |
|---|---|---|
| Fire & Ice | `fire_and_ice.jpg` | icy blue + ember orange |
| Alone | `alone_lofi.jpg` | dark, moody, glowing blue |
| Neon Marble | `neon_marble.jpg` | vivid pink/magenta |
| Forest Campfire | `forest_campfire.jpg` | warm orange/brown |
| Autumn Canopy | `autumn_canopy.jpg` | teal + burnt orange |

They're reachable from the **palette icon** in the library screen's top
bar, which opens `ThemePickerScreen` — a list of the 5 presets plus
"Automatic (match cover art)". Picking a preset pins it: the app stops
re-theming per track and uses that palette everywhere (animated
background, app bars) until you switch back to Automatic. The choice is
saved via `AppState`/SQLite, so it survives a restart.

Palette extraction got an upgrade to support this well: the original
"most frequent pixel" approach picked near-black shadow on busy photos
(useless for a themed palette). It now scores quantized colors by
saturation as well as frequency, so a photo's actual signature color
(the fire-orange, the neon pink) wins over a sea of dark background —
this improved version is what both the presets *and* live cover-art
theming use now.

If what you actually meant was "tie a specific image to a specific
song/album" rather than a manual picker, that's a small change: swap the
picker-driven lookup in `player_screen._resolve_theme()` for a lookup
keyed on `track.album` (or a name-mapping file you maintain) instead of
a stored user selection — say the word and I'll make that swap.

## Known limitations / next steps

- Playback uses Kivy's `SoundLoader`, which is fine for mp3/wav/ogg but
  format support depends on the audio provider available on-device
  (ffpyplayer is bundled via the `kivy` requirement). For gapless
  playback or background-service playback with a persistent
  notification (like the real Samsung Music app), you'd want to move
  playback into an Android foreground `Service` via `pyjnius` — that's a
  meaningfully bigger lift and worth doing as a separate pass once the
  core UI feels right.
- No background/lock-screen media controls yet (`MediaSession` +
  notification) — flagging since "like Samsung Music" implies that.
- Search/sort/playlists beyond favorites aren't built yet — easy to add
  as another screen once you confirm priority.
