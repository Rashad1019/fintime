"""SQLite-backed watchlist persistence (watchlist.db in the project root)."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "watchlist.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tickers ("
        "symbol TEXT PRIMARY KEY, "
        "added_at TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    return conn


def add_ticker(symbol: str) -> None:
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO tickers (symbol) VALUES (?)",
                (symbol.strip().upper(),),
            )
    finally:
        conn.close()


def remove_ticker(symbol: str) -> None:
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "DELETE FROM tickers WHERE symbol = ?", (symbol.strip().upper(),)
            )
    finally:
        conn.close()


def list_tickers() -> list[str]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT symbol FROM tickers ORDER BY symbol").fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()
