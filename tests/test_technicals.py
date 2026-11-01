import numpy as np
import pandas as pd
import pytest

from analytics import technicals


def _series(values) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2025-01-01", periods=len(values)))


RISING = _series(np.linspace(100, 200, 250))
FALLING = _series(np.linspace(200, 100, 250))


class TestRsi:
    def test_rising_prices_give_high_rsi(self):
        value = technicals.rsi(RISING)
        assert value is not None
        assert value > 70

    def test_falling_prices_give_low_rsi(self):
        value = technicals.rsi(FALLING)
        assert value is not None
        assert value < 30

    def test_rsi_stays_within_bounds(self):
        rng = np.random.default_rng(42)
        noisy = _series(100 + rng.normal(0, 2, 300).cumsum())
        value = technicals.rsi(noisy)
        assert 0 <= value <= 100

    def test_insufficient_data_returns_none(self):
        assert technicals.rsi(_series([100.0, 101.0, 102.0])) is None


class TestSummary:
    def test_summary_has_all_keys(self):
        summary = technicals.build_summary(RISING)
        for key in ("price", "rsi_14", "sma_20", "sma_50", "sma_200", "return_1mo"):
            assert key in summary

    def test_short_history_yields_none_smas(self):
        summary = technicals.build_summary(_series(np.linspace(100, 110, 30)))
        assert summary["sma_200"] is None
        assert summary["sma_20"] is not None


class TestSignals:
    def test_falling_prices_suggest_oversold_entry(self):
        summary = technicals.build_summary(FALLING)
        suggestions = technicals.enter_suggestions(summary)
        assert any("oversold" in s.lower() for s in suggestions)

    def test_rising_prices_suggest_overbought_exit(self):
        summary = technicals.build_summary(RISING)
        suggestions = technicals.exit_suggestions(summary)
        assert any("overbought" in s.lower() for s in suggestions)

    def test_falling_prices_flag_broken_trend(self):
        summary = technicals.build_summary(FALLING)
        suggestions = technicals.exit_suggestions(summary)
        assert any("200-day" in s for s in suggestions)

    def test_no_signals_returns_wait_message(self):
        summary = {
            "price": 100.0,
            "rsi_14": 50.0,
            "sma_20": 100.0,
            "sma_50": 99.0,
            "sma_200": 101.0,
            "return_1mo": 0.0,
        }
        entries = technicals.enter_suggestions(summary)
        assert len(entries) == 1
        assert "no entry signals" in entries[0].lower()


class TestSentiment:
    def test_rising_prices_are_bullish(self):
        verdict = technicals.sentiment(technicals.build_summary(RISING))
        assert verdict["label"] == "Bullish"
        assert verdict["score"] > 0
        assert verdict["reasons"]

    def test_falling_prices_are_bearish(self):
        verdict = technicals.sentiment(technicals.build_summary(FALLING))
        assert verdict["label"] == "Bearish"
        assert verdict["score"] < 0

    def test_missing_indicators_lean_neutral(self):
        summary = {
            "price": 100.0,
            "rsi_14": None,
            "sma_20": None,
            "sma_50": None,
            "sma_200": None,
            "return_1mo": None,
        }
        verdict = technicals.sentiment(summary)
        assert verdict["label"] == "Neutral"


def _summary(price, rsi=50.0, sma_50=None, sma_200=None):
    return {"price": price, "rsi_14": rsi, "sma_50": sma_50, "sma_200": sma_200}


def test_period_return_compares_first_and_last():
    assert technicals.period_return(pd.Series([100.0, 90.0, 110.0])) == pytest.approx(0.10)
    assert technicals.period_return(pd.Series([100.0])) is None


def test_entry_read_says_wait_when_overbought_even_in_an_uptrend():
    summary = _summary(120.0, rsi=75.0, sma_50=110.0, sma_200=100.0)
    assert technicals.entry_read(summary)["label"] == "Wait"


def test_entry_read_says_wait_below_the_200_day_average():
    assert technicals.entry_read(_summary(90.0, rsi=25.0, sma_200=100.0))["label"] == "Wait"


def test_entry_read_is_cautious_about_a_pullback_in_an_uptrend():
    summary = _summary(105.0, rsi=40.0, sma_50=110.0, sma_200=100.0)
    assert technicals.entry_read(summary)["label"] == "Possible entry"


def test_entry_read_likes_an_intact_uptrend():
    summary = _summary(120.0, rsi=55.0, sma_50=110.0, sma_200=100.0)
    assert technicals.entry_read(summary)["label"] == "Good entry"


def test_entry_read_has_no_opinion_without_long_history():
    assert technicals.entry_read(_summary(100.0))["label"] == "No clear signal"


def _chart(price, sma_50=None, sma_200=None, rsi_14=50.0):
    return {"price": price, "sma_50": sma_50, "sma_200": sma_200, "rsi_14": rsi_14}


def test_price_levels_picks_the_nearest_level_above_the_trend_line():
    prices = pd.Series([100.0] * 60 + [95.0] + [100.0] * 2)
    levels = technicals.price_levels(prices, _chart(100.0, sma_50=98.0, sma_200=90.0))
    assert levels == {"better_price": 98.0, "trend_line": 90.0}


def test_price_levels_skips_a_dip_too_small_to_wait_for():
    prices = pd.Series([100.0] * 70)
    levels = technicals.price_levels(prices, _chart(100.0, sma_50=99.5, sma_200=90.0))
    assert levels["better_price"] is None


def test_price_levels_never_offers_a_price_under_the_trend_line():
    prices = pd.Series([85.0] + [100.0] * 62)
    levels = technicals.price_levels(prices, _chart(100.0, sma_50=99.9, sma_200=90.0))
    assert levels["better_price"] is None


def test_buy_answer_below_the_trend_says_when_to_look_again():
    summary = _chart(80.0, sma_50=85.0, sma_200=90.0)
    result = technicals.buy_answer(summary, {"better_price": None, "trend_line": 90.0}, "USD")
    assert result["answer"] == "Not yet"
    assert "climbs back above 90.00 USD" in result["next_step"]


def test_buy_answer_on_a_pullback_gives_both_prices():
    summary = _chart(100.0, sma_50=105.0, sma_200=90.0, rsi_14=40.0)
    result = technicals.buy_answer(summary, {"better_price": 95.0, "trend_line": 90.0}, "USD")
    assert result["answer"] == "Maybe, but there's no rush"
    assert "95.00 USD" in result["next_step"]
    assert "falls below 90.00 USD" in result["next_step"]


def test_buy_answer_works_without_enough_history():
    result = technicals.buy_answer(_chart(100.0), {"better_price": None, "trend_line": None}, None)
    assert result == {"answer": "No rush", "next_step": ""}
