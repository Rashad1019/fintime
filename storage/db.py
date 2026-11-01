"""SQLite persistence for saved persona runs.

The database location resolves in order: explicit db_path argument,
FINCENT_DB_PATH environment variable, watchlist.db in the project root.
Tests pass a temp path so they never touch the real database.
"""

import json
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
        "CREATE TABLE IF NOT EXISTS agent_runs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ticker TEXT NOT NULL, "
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP, "
        "prompt TEXT NOT NULL, "
        "results_json TEXT NOT NULL)"
    )
    return conn


def save_agent_run(
    ticker: str, prompt: str, results: list[dict], db_path: PathLike = None
) -> int:
    """Store one finished persona run and return its id."""
    conn = _connect(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO agent_runs (ticker, prompt, results_json) VALUES (?, ?, ?)",
                (ticker.strip().upper(), prompt, json.dumps(results)),
            )
        return int(cursor.lastrowid)
    finally:
        conn.close()


def latest_agent_run(ticker: str, db_path: PathLike = None) -> dict | None:
    """Most recent saved run for a ticker, or None."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, ticker, created_at, prompt, results_json "
            "FROM agent_runs WHERE ticker = ? ORDER BY id DESC LIMIT 1",
            (ticker.strip().upper(),),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "id": row[0],
        "ticker": row[1],
        "created_at": row[2],
        "prompt": row[3],
        "results": json.loads(row[4]),
    }
