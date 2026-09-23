"""Persistent login attempt budget shared by workers on the same volume."""
import hashlib
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path


class LoginAttemptStore:
    def __init__(self, path):
        self.path = Path(path)

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('CREATE TABLE IF NOT EXISTS attempts (key TEXT NOT NULL, at REAL NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS attempts_key ON attempts(key, at)')
        return db

    @staticmethod
    def _key(key):
        return hashlib.sha256(repr(key).encode()).hexdigest()

    def reserve(self, key, limit, window):
        now = time.time()
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE at <= ?', (now - window,))
            count = db.execute('SELECT count(*) FROM attempts WHERE key = ?', (self._key(key),)).fetchone()[0]
            if count >= limit:
                return False
            db.execute('INSERT INTO attempts (key, at) VALUES (?, ?)', (self._key(key), now))
            return True

    def get(self, key, default=None):
        with closing(self._connect()) as db:
            rows = db.execute('SELECT at FROM attempts WHERE key = ?', (self._key(key),)).fetchall()
        return [r[0] for r in rows] if rows else default

    def pop(self, key, default=None):
        with closing(self._connect()) as db, db:
            db.execute('DELETE FROM attempts WHERE key = ?', (self._key(key),))

    def clear(self):
        with closing(self._connect()) as db, db:
            db.execute('DELETE FROM attempts')
