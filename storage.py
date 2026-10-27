"""
storage.py

Tiny SQLite wrapper for things that must persist across app launches:
  * favorites  -> which track ids the user has starred
  * app_state  -> misc key/value (last played track, volume, etc.)

Kept deliberately simple (no ORM) since the data model is small.
"""

from __future__ import annotations

import os
import sqlite3
from typing import List

try:
    from android.storage import app_storage_path  # type: ignore
    DB_DIR = app_storage_path()
except Exception:
    DB_DIR = os.path.expanduser("~/.sumbeat")

os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "sumbeat.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    return conn


class FavoritesStore:
    def is_favorite(self, track_id: str) -> bool:
        with _connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorites WHERE track_id = ?", (track_id,)
            ).fetchone()
            return row is not None

    def toggle(self, track_id: str) -> bool:
        """Flip favorite status, return the new state."""
        with _connect() as conn:
            if self.is_favorite(track_id):
                conn.execute("DELETE FROM favorites WHERE track_id = ?", (track_id,))
                conn.commit()
                return False
            conn.execute("INSERT OR IGNORE INTO favorites (track_id) VALUES (?)", (track_id,))
            conn.commit()
            return True

    def all_ids(self) -> List[str]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT track_id FROM favorites ORDER BY added_at DESC"
            ).fetchall()
            return [r[0] for r in rows]


class AppState:
    def get(self, key: str, default=None):
        with _connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_state WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else default

    def set(self, key: str, value: str):
        with _connect() as conn:
            conn.execute(
                "INSERT INTO app_state (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()
