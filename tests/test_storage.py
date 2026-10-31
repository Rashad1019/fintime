from storage import db


def test_add_and_list_tickers(tmp_path):
    path = tmp_path / "watchlist.db"
    db.add_ticker("MSFT", db_path=path)
    db.add_ticker("AAPL", db_path=path)
    assert db.list_tickers(db_path=path) == ["AAPL", "MSFT"]


def test_add_normalizes_case_and_whitespace(tmp_path):
    path = tmp_path / "watchlist.db"
    db.add_ticker("  msft ", db_path=path)
    assert db.list_tickers(db_path=path) == ["MSFT"]


def test_duplicate_add_is_ignored(tmp_path):
    path = tmp_path / "watchlist.db"
    db.add_ticker("MSFT", db_path=path)
    db.add_ticker("msft", db_path=path)
    assert db.list_tickers(db_path=path) == ["MSFT"]


def test_remove_ticker(tmp_path):
    path = tmp_path / "watchlist.db"
    db.add_ticker("MSFT", db_path=path)
    db.remove_ticker("msft", db_path=path)
    assert db.list_tickers(db_path=path) == []


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
    db.add_ticker("SCHD")
    assert db.list_tickers() == ["SCHD"]
    assert path.exists()
