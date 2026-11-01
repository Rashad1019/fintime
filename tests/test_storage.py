from storage import db


def test_agent_run_round_trip_returns_latest_for_ticker(tmp_path):
    path = tmp_path / "watchlist.db"
    db.save_agent_run("aapl", "prompt-1", [{"persona": "Warren Buffett", "verdict": "HOLD"}], db_path=path)
    db.save_agent_run("aapl", "prompt-2", [{"persona": "Cathie Wood", "verdict": "BUY"}], db_path=path)
    db.save_agent_run("msft", "other", [{"persona": "Jack Bogle"}], db_path=path)

    latest = db.latest_agent_run("AAPL", db_path=path)

    assert latest["ticker"] == "AAPL"
    assert latest["prompt"] == "prompt-2"
    assert latest["results"][0]["persona"] == "Cathie Wood"
    assert db.latest_agent_run("ZZZZ", db_path=path) is None


def test_env_var_overrides_default_path(tmp_path, monkeypatch):
    path = tmp_path / "custom.db"
    monkeypatch.setenv("FINCENT_DB_PATH", str(path))
    db.save_agent_run("SCHD", "prompt", [])
    assert db.latest_agent_run("SCHD")["prompt"] == "prompt"
    assert path.exists()
