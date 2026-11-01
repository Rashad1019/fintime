from agents.recommendations import classify, pick_replacements, slammed


def test_slammed_when_most_verdicts_are_avoid():
    assert slammed([{"verdict": "Skip"}, {"verdict": "Skip"}, {"verdict": "Wait"}])
    assert not slammed([{"verdict": "Buy now"}, {"verdict": "Skip"}])
    assert not slammed([{"verdict": None}])


def test_qqqi_is_a_nasdaq_income_product():
    assert classify("QQQI", "NEOS NASDAQ-100 High Income ETF") == "nasdaq_income"


def test_replacements_include_a_role_fund_and_a_near_price():
    quotes = {
        "QQQ": {"name": "Invesco QQQ", "price": 480.0},
        "QQQM": {"name": "Invesco NASDAQ 100", "price": 48.0},
        "SPLG": {"name": "SPDR Portfolio S&P 500", "price": 70.0},
        "JEPI": {"name": "JPMorgan Equity Premium Income", "price": 55.0},
    }

    picks = pick_replacements(
        "QQQI",
        50.0,
        "NEOS NASDAQ-100 High Income ETF",
        quotes,
    )

    by_slot = {pick["slot"]: pick["ticker"] for pick in picks}
    assert by_slot["role"] == "QQQM"
    assert by_slot["price"] == "JEPI"
    assert "50.00" in picks[1]["reason"] or "$50.00" in picks[1]["reason"]


def test_role_can_be_far_away_when_nothing_cheap_shares_the_job():
    quotes = {
        "QQQ": {"name": "Invesco QQQ", "price": 480.0},
        "JEPI": {"name": "JPMorgan Equity Premium Income", "price": 55.0},
    }

    picks = pick_replacements("QQQI", 50.0, "NASDAQ-100 High Income ETF", quotes)

    assert [pick["ticker"] for pick in picks] == ["QQQ", "JEPI"]
    assert "10% from QQQI" in picks[1]["reason"]


def test_does_not_recommend_the_ticker_itself():
    quotes = {
        "QQQM": {"name": "Invesco NASDAQ 100", "price": 48.0},
        "QQQI": {"name": "NEOS", "price": 50.0},
        "JEPI": {"name": "JEPI", "price": 55.0},
    }
    tickers = {pick["ticker"] for pick in pick_replacements("QQQI", 50.0, "income etf nasdaq", quotes)}
    assert "QQQI" not in tickers
