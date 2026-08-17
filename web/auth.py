import sqlite3
from pathlib import Path

from passlib.hash import bcrypt

DB_PATH = Path(__file__).parent / "usuarios.db"


class EmailDuplicadoError(Exception):
    pass


def get_conn(db_path=None):
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            creado TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def crear_usuario(conn, nombre, email, password, creado):
    email = email.strip().lower()
    existente = conn.execute(
        "SELECT 1 FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    if existente:
        raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}")
    password_hash = bcrypt.hash(password)
    conn.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, creado) VALUES (?, ?, ?, ?)",
        (nombre, email, password_hash, creado),
    )
    conn.commit()


def verificar_usuario(conn, email, password):
    email = email.strip().lower()
    fila = conn.execute(
        "SELECT id, nombre, email, password_hash FROM usuarios WHERE email = ?",
        (email,),
    ).fetchone()
    if fila is None:
        return None
    id_, nombre, email_db, password_hash = fila
    if not bcrypt.verify(password, password_hash):
        return None
    return {"id": id_, "nombre": nombre, "email": email_db}
