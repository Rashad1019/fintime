# Fincept-Lite: Personal Research Terminal (Python/Streamlit)

## Context
Rashad wants a personal-use financial research tool inspired by Fincept Terminal (DCF, ratios, risk metrics, market data) — no broker connections, no accounts/billing, no cloud infra. It must run well both on his desktop and be reachable from his phone. Starting point is an empty directory. He also wants this built "the best" way, i.e. clean, testable, production-quality code even though the audience is just himself — so it's a foundation he isn't forced to rewrite later if he ever wants to extend it.

## Approach: Streamlit app, served over local network, reachable by phone browser
A Python desktop app can't be opened on a phone, and a full FastAPI+React+auth stack is scope built for other people, not one user. Streamlit gives a real web UI from pure Python, runs on the desktop, and Streamlit's `--server.address 0.0.0.0` flag makes it reachable from a phone browser on the same WiFi at `http://<pc-local-ip>:8501` — zero extra hosting, zero accounts. Business logic is written as plain Python modules Streamlit calls into (not stuffed in the UI script), so it's independently testable and portable to a different UI later if ever needed.

## Data sources
- **yfinance** (primary) — free, no key, Yahoo Finance under the hood. Matches what Fincept itself uses.
- **Yahoo chart API direct** (fallback) — free, no key. Stooq (the original choice) blocks scripted downloads with a browser-verification challenge, so the fallback instead calls Yahoo's raw JSON chart endpoint with plain `requests`, which keeps price history working even if the yfinance library itself breaks.
- **FRED** (optional, later) — free but requires a personal API key; only add if/when macro data (rates, GDP, inflation) is wanted.

## Investor-persona AI agents (included from day one, via OpenRouter)
Fincept's 37 agents modeled on Buffett, Munger, Graham, Lynch, Klarman, Marks are re-created here as prompt templates run through **OpenRouter** (existing key) — one API for many models, no local install, and free-tier models (e.g. Llama/Gemini free variants) available to keep cost near zero. Model choice lives in one config value (`OPENROUTER_MODEL`) so it can be upgraded later without touching agent logic. Key is read from an environment variable (`OPENROUTER_API_KEY`), never hardcoded.

Each persona is a system prompt encoding that investor's known framework (e.g. Munger: mental models, moats, avoiding stupidity; Graham: margin of safety, quantitative screens) fed the ticker's fundamentals/ratios already computed by `analytics/`. This keeps agents grounded in real computed numbers rather than the model inventing figures.

## Project structure
```
fincent/
├── app.py                  # Streamlit entrypoint / page router
├── pages/
│   ├── 1_Quote.py           # ticker lookup, price chart, key stats
│   ├── 2_Watchlist.py       # saved tickers, SQLite-backed
│   ├── 3_Analytics.py       # DCF calculator, risk metrics (VaR, Sharpe)
│   └── 4_Agents.py          # pick a ticker + a persona, get analysis
├── data/
│   ├── __init__.py
│   ├── yfinance_source.py  # fetch quote/history/fundamentals, cached
│   └── stooq_source.py     # fallback price fetch
├── analytics/
│   ├── __init__.py
│   ├── ratios.py            # P/E, P/B, ROE, margins from raw fundamentals
│   ├── dcf.py                # discounted cash flow calculator
│   └── risk.py               # volatility, Sharpe ratio, VaR
├── agents/
│   ├── __init__.py
│   ├── personas.py          # persona system prompts (Munger, Buffett, Graham, Lynch, Klarman, Marks)
│   └── openrouter_client.py # OpenRouter API wrapper, reads OPENROUTER_API_KEY from env
├── storage/
│   ├── __init__.py
│   └── db.py                 # SQLite watchlist persistence
├── tests/
│   ├── test_ratios.py
│   ├── test_dcf.py
│   ├── test_risk.py
│   └── test_personas.py      # prompt template builds correctly given sample data
├── .env.example              # OPENROUTER_API_KEY=
├── requirements.txt
└── .gitignore                # excludes .env, watchlist.db
```

## Build order
1. **Scaffold**: git init, venv, `requirements.txt` (streamlit, yfinance, pandas, numpy, pytest), folder structure, `.gitignore`.
2. **Data layer**: `yfinance_source.py` with `get_quote(ticker)`, `get_history(ticker, period)`, `get_fundamentals(ticker)` — each wrapped in try/except that falls back to `stooq_source.py` for price data on failure. Cache results with `@st.cache_data(ttl=...)` to avoid re-hitting the API on every rerun.
3. **Analytics (pure functions, no Streamlit imports)** — these carry the 80% test-coverage bar since they're the part most likely to have real bugs:
   - `ratios.py`: P/E, P/B, ROE, debt/equity, margins from fundamentals dict.
   - `dcf.py`: DCF value given FCF, growth rate, discount rate, terminal growth.
   - `risk.py`: annualized volatility, Sharpe ratio, historical VaR from a price series.
4. **Tests first** for each analytics module (`tests/test_*.py`) — known input → known expected output, plus edge cases (zero/negative earnings, empty price series).
5. **Storage**: `storage/db.py` — SQLite file (`watchlist.db`) with a simple `tickers` table; `add`, `remove`, `list` functions.
6. **UI — Quote page**: ticker input → price chart (via `st.line_chart` or plotly) + key stats table + computed ratios.
7. **UI — Watchlist page**: add/remove tickers, table of current prices for the list, powered by `storage/db.py`.
8. **UI — Analytics page**: DCF calculator form (inputs → intrinsic value output) and risk metrics for a chosen ticker/watchlist.
9. **Agents**: `agents/personas.py` defines each investor's system prompt as a template accepting computed ratios/DCF/fundamentals; `agents/openrouter_client.py` sends the built prompt to OpenRouter (model from `OPENROUTER_MODEL` env var, default to a free-tier model) and returns the response. `.env` (git-ignored) holds `OPENROUTER_API_KEY`; `.env.example` documents the required variable without the real value.
10. **UI — Agents page**: pick a ticker + a persona (or "run all personas"), show each agent's take alongside the underlying numbers it was given, so it's clear the analysis is grounded in real data, not invented.
11. **Polish**: loading spinners during fetch/LLM calls, explicit error messages when yfinance/Stooq/OpenRouter fail, confirm layout doesn't break on a phone-width viewport.
12. **Run for mobile access**: `streamlit run app.py --server.address 0.0.0.0`, then open `http://<pc-local-ip>:8501` from phone on same WiFi.

## Verification
- `pytest` — all analytics and persona-prompt-building tests pass, confirms coverage on ratios/DCF/risk logic.
- `streamlit run app.py` on desktop — manually check Quote, Watchlist, Analytics, and Agents pages load real data for a few tickers (e.g. AAPL, MSFT).
- From phone browser on same WiFi, hit `http://<pc-local-ip>:8501` and confirm the app renders and a quote lookup + one agent run both work.
- Force a yfinance failure (bad ticker or temporarily rename the function call) to confirm Stooq fallback path actually fires instead of crashing.
- Run one persona against a real ticker and confirm the response references the actual computed numbers passed in, not fabricated ones.
- Confirm `OPENROUTER_API_KEY` is never committed to git (check `.gitignore` covers `.env`).
