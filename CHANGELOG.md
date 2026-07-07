# Changelog

Newest first. Commit hashes refer to the GitHub repo (Rashad1019/fintime).

## Intraday periods + candlestick charts — `8343512` (2026-07-06)

**What:** The Quote page chart got three new time periods and a second chart style.

- **New periods: 1h, 1d, 1wk** alongside the existing 1mo–5y. Each period is
  paired with the right bar size in `config.py` (1h → 1-minute bars, 1d →
  5-minute bars, 1wk → 15-minute bars, longer → daily bars).
- **Line / Candles toggle** — candlesticks render with Plotly (green up,
  red down, zoomable). Falls back to a line chart with a note if the data
  source can't supply Open/High/Low.
- **Data layer returns full OHLC** instead of Close only, from both the
  yfinance path and the raw chart-API fallback.
- Known limits (free Yahoo data): market closed → 1h shows the last trading
  hour; 1-minute bars only exist for ~7 days back.
- Tests: 58 total (added fallback OHLC parsing, safe defaults for bad
  period/interval).

## Architecture refactor — `169d9ec` (2026-07-06)

**What:** Applied the findings from the senior-engineer code review. No feature
changes — same app, sturdier internals. Full design in `ARCHITECTURE.md`.

- **One API call instead of two (H1):** a single `.info` fetch now produces a
  "snapshot" (quote + fundamentals + source marker), so the two can never
  disagree and Yahoo is hit half as often.
- **No more silent failures (H2):** every `except Exception: pass` removed.
  Fallbacks log warnings with tracebacks, and the UI *shows* degraded data —
  a warning banner on Quote, a ⚠ marker on Watchlist rows.
- **Parallel watchlist (H3):** quotes fetch concurrently in a thread pool
  instead of one at a time — load time no longer grows linearly with list size.
- **Pure data layer (M3):** fetching/parsing (`data/yahoo.py`) is now plain
  Python with no Streamlit import; caching lives in a thin facade
  (`data/cache.py`). Scripts and tests can reuse the data layer directly.
- **One source of truth (M1, M2):** DCF assumptions moved to `config.py`
  (Analytics and Agents can't drift apart); persona prompts use the same
  `formatting.py` helpers as the UI.
- **Testable storage (M4):** watchlist DB path is injectable
  (argument → `FINCENT_DB_PATH` env var → project root), so tests never touch
  the real watchlist.
- **Refreshable model list (M6):** `OPENROUTER_MODELS` in `.env` overrides the
  hardcoded free-model rotation — no code edit when free tiers disappear.
- **Test coverage (M5):** 30 → 56 tests; new suites for Yahoo parsing,
  fallback degradation, OpenRouter model rotation, storage, and formatting.
  All offline — no network needed to run `uv run pytest`.
- Also added: `run.bat` (double-click launcher), `AGENTS.md` / `agents.html`
  (persona reference docs), `ARCHITECTURE.md`.

## Initial build — `5879a36` (2026-07-05)

**What:** Fincent v1 — personal research terminal built test-first
(Python, Streamlit, uv).

- Four pages: **Quote** (price chart + valuation ratios), **Watchlist**
  (SQLite-backed), **Analytics** (DCF intrinsic value + volatility/Sharpe/VaR),
  **Agents** (ticker's real computed numbers analyzed by 20 investor
  personas via OpenRouter — Buffett, Graham, Lynch, Burry, Cathie Wood,
  Bogle, Ian Dunlap, Wall Street Trapper, and more).
- Data from Yahoo Finance (no API key) with a raw chart-API fallback.
- 30 tests covering the analytics math and persona prompts.
- Deployed to Streamlit Community Cloud; API key kept in `.env` locally and
  in cloud Secrets — never committed.
