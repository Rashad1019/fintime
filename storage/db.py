"""SQLite-backed watchlist persistence.

The database location resolves in order: explicit db_path argument,
FINCENT_DB_PATH environment variable, watchlist.db in the project root.
Tests pass a temp path so they never touch the real watchlist.
"""

import os
import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "watchlist.db"

PathLike = Path | str | None


def _resolve_db_path(db_path: PathLike) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(os.getenv("FINCENT_DB_PATH") or _DEFAULT_DB_PATH)


def _connect(db_path: PathLike = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_db_path(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tickers ("
        "symbol TEXT PRIMARY KEY, "
        "added_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    return conn


def add_ticker(symbol: str, db_path: PathLike = None) -> None:
    conn = _connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO tickers (symbol) VALUES (?)",
                (symbol.strip().upper(),),
            )
    finally:
        conn.close()


def remove_ticker(symbol: str, db_path: PathLike = None) -> None:
    conn = _connect(db_path)
    try:
        with conn:
            conn.execute(
                "DELETE FROM tickers WHERE symbol = ?", (symbol.strip().upper(),)
            )
    finally:
        conn.close()


def list_tickers(db_path: PathLike = None) -> list[str]:
    conn = _connect(db_path)
    try:
        rows = conn.execute("SELECT symbol FROM tickers ORDER BY symbol").fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()
