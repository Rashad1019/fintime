# Fincent Architecture

Personal financial research terminal: Streamlit UI over a layered Python core.
Rule of the house: **UI at the edges, pure logic in the middle.** Only `pages/`,
`app.py`, and `data/cache.py` may import Streamlit; everything else is plain
Python that works from scripts and tests.

## Layers and data flow

```
Browser
  │
  ▼
app.py + pages/            Streamlit UI (widgets, spinners, error display)
  │           │
  │           ▼
  │      config.py          shared constants (DCF assumptions, periods)
  ▼
data/cache.py              st.cache_data facade + parallel watchlist fetch
  │                        (the ONLY data module pages import)
  ▼
data/yahoo.py              pure fetch/parse: ONE .info call → snapshot
  │            └─ on failure ─▶ data/fallback_source.py (raw Yahoo chart API)
  ▼
analytics/                 pure math: ratios.py, dcf.py, risk.py
agents/                    personas.py (prompts) + openrouter_client.py (LLM)
storage/db.py              SQLite watchlist (path injectable)
formatting.py              single source of display formatting (UI + prompts)
```

**The snapshot** is the core data contract, produced by `yahoo.fetch_snapshot`:

```python
{
  "quote":        {ticker, name, price, market_cap, currency},
  "fundamentals": {...} | None,          # None on the degraded path
  "source":       "yahoo" | "fallback",  # UI shows a warning when degraded
}
```

One `yf.Ticker(t).info` call produces both quote and fundamentals, so they can
never disagree and the API is hit half as often. Stocks add one balance-sheet
call for equity, and one FX call when the company reports in a different
currency than its shares trade in. Fundamentals are always in the trading
currency, so per-share figures can be compared with the price. FMP data gets
the same treatment. FX rates and backup dividends come from the raw chart API,
which still answers on hosts where the yfinance library is blocked.

## Design decisions (and why)

| Decision | Why |
|---|---|
| `data/yahoo.py` is Streamlit-free; caching lives in `data/cache.py` | Scripts, tests, and future features (alerts, screeners) can reuse fetching without a Streamlit runtime |
| Snapshot marks its `source`; pages surface a ⚠ when degraded | The old code silently fell back — you could analyze N/A-filled data for days without knowing |
| Failures are logged (`logging.getLogger(__name__)`, warnings to stderr) | The old `except Exception: pass` destroyed the evidence needed to debug data outages |
| Watchlist fetches run in a `ThreadPoolExecutor` inside one cached function | Fixes the N+1 serial loop; threads run only pure code, so no Streamlit-context issues |
| `config.py` owns DCF assumptions and period lists | Analytics and Agents previously had separate copies that could silently drift |
| `formatting.py` is used by both pages and persona prompts | One percent/ratio/money format everywhere; prompt numbers match what the UI shows |
| `storage/db.py` resolves path: argument → `FINCENT_DB_PATH` → project root | Tests use `tmp_path` and can never touch the real watchlist |
| `OPENROUTER_MODELS` env var overrides the hardcoded free-model rotation | Free-tier models get removed upstream; refresh the list without a code change |
| Analytics returns `None` for undefined (P/E with negative EPS), raises `ValueError` for invalid input, data layer raises `DataSourceError` | "No answer" and "bad request" and "source down" are different situations and pages handle them differently |

## Error-handling conventions

- **`DataSourceError`** — raised by `data/` when no source can provide data;
  pages show `st.error` and stop.
- **`OpenRouterError`** — raised by the LLM client with an actionable message
  (missing key, all models rate-limited, bad response shape).
- **Degradation over failure** — quotes fall back to the chart API's last
  close and are *marked*, never silently substituted.
- **No swallowed exceptions** — every fallback path logs a warning with
  `exc_info` before proceeding.

## Testing

`uv run pytest` — 56 tests, no network required:

- `test_ratios / test_dcf / test_risk / test_personas` — pure math and prompts
- `test_yahoo_parsing` — info-dict parsing, dividend-yield normalization,
  fallback degradation (yfinance monkeypatched to fail), chart-payload parsing
- `test_openrouter_client` — model rotation on 429/404, env overrides,
  fail-fast on non-retryable errors (fake HTTP responses)
- `test_storage` — temp-file DB round-trips, normalization, env path override
- `test_formatting` — ratio/percent/money rendering

## Known limits (accepted for a single-user app)

- `get_snapshots` caches on the whole ticker tuple — adding one symbol
  refetches all (in parallel, so cheap at personal watchlist sizes).
- Snapshot TTL is 300s for fundamentals too (was 3600s) — slightly more
  fetches in exchange for quote/fundamentals never drifting apart.
- On Streamlit Community Cloud the SQLite watchlist is ephemeral and shared
  across viewers — keep the app restricted to your own account.
