[app]
title = SumBeat
package.name = sumbeat
package.domain = org.sumbeat

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 0.1.0

# Runtime deps pulled in during the Android build
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,mutagen,pyjnius

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/music_app/assets/default_cover.png

[app:android]
# Scoped-storage-aware audio permission (Android 13+) plus the legacy one
# for older devices. Buildozer/p4a will only request what's relevant to
# the target SDK, but declaring both keeps us compatible either way.
android.permissions = READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS

android.api = 34
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Needed so MediaStore queries + mutagen file reads work against real paths
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
