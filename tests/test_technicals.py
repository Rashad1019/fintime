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
