"""Agents page: run a ticker's computed numbers past investor personas."""

import pandas as pd
import streamlit as st

import ui
from agents import openrouter_client
from agents.metrics import assemble_metrics
from agents.personas import PERSONAS, PROFILE_BY_NAME, build_prompt, profiles_by_group
from agents.recommendations import CANDIDATES, pick_replacements, slammed
from agents.verdicts import parse_verdict
from config import (
    DCF_DISCOUNT,
    DCF_GROWTH,
    DCF_SLOW_GROWTH,
    DCF_STRESS_DISCOUNT,
    DCF_TERMINAL_GROWTH,
    DCF_YEARS,
    RISK_HISTORY_PERIOD,
)
from data import DataSourceError, cache
from storage import db

def _history_or_empty(symbol: str, period: str, data_provider: str) -> pd.Series:
    try:
        frame = cache.get_history(symbol, period, provider=data_provider, adjusted=False)
    except DataSourceError:
        return pd.Series(dtype=float)
    if frame is None or frame.empty or "Close" not in frame.columns:
        return pd.Series(dtype=float)
    return frame["Close"]


def _show_replacements(symbol: str, data_provider: str, results: list[dict]) -> None:
    try:
        snapshot = cache.get_snapshot(symbol, data_provider)
    except DataSourceError:
        return
    quote = (snapshot or {}).get("quote") or {}
    fetched = cache.get_snapshots(tuple(sorted(CANDIDATES)), data_provider)
    quotes = {
        candidate: (snap or {}).get("quote")
        for candidate, snap in fetched.items()
        if snap and snap.get("quote")
    }
    picks = pick_replacements(symbol, quote.get("price"), quote.get("name"), quotes)
    if not picks:
        return
    title = f"Instead of {symbol}" if slammed(results) else f"Two ideas next to {symbol}"
    st.subheader(title)
    columns = st.columns(len(picks))
    labels = {"role": "In its place", "price": "Close in price"}
    for column, pick in zip(columns, picks):
        column.markdown(f"**{labels[pick['slot']]} · {pick['ticker']}**")
        column.caption(pick["reason"])


def _show_comparison(results: list[dict]) -> None:
    rows = []
    for result in results:
        conviction = result.get("conviction")
        rows.append(
            {
                "Persona": result["persona"],
                "Verdict": result.get("verdict") or "—",
                "Conviction": conviction if conviction is not None else "—",
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


ui.apply_theme()
ui.page_header(
    "Investor agents",
    "Framework studio / 16 perspectives",
    "Run real computed ratios, DCF, risk, and technicals through distinct investor frameworks.",
)
provider = ui.select_provider()

with st.expander("Who these personas are", expanded=True):
    for group, profiles in profiles_by_group():
        st.markdown(f"**{group}**")
        for profile in profiles:
            st.markdown(f"**{profile.name}** — {profile.summary}")

col_ticker, col_persona = st.columns([1, 2])
ticker = col_ticker.text_input("Ticker", value="AAPL").strip().upper()
persona_names = list(PERSONAS.keys())
selected = col_persona.multiselect(
    "Personas", persona_names, default=persona_names[:1]
)
for name in selected:
    profile = PROFILE_BY_NAME[name]
    st.caption(f"{profile.group} · {profile.summary}")

if st.button("Run analysis", type="primary") and ticker and selected:
    try:
        with st.spinner(f"Computing metrics for {ticker}..."):
            snapshot = cache.get_snapshot(ticker, provider)
            history = cache.get_history(ticker, RISK_HISTORY_PERIOD, provider=provider)
            dividend_prices = _history_or_empty(ticker, "5y", provider)
            dividends = cache.get_dividends(ticker)
            macro = cache.get_macro()
    except DataSourceError as exc:
        st.error(str(exc))
        st.stop()

    ui.show_source_banner(snapshot["source"], provider)
    fundamentals = snapshot["fundamentals"]
    if fundamentals is None:
        st.error(
            f"No fundamentals available for '{ticker}' right now — the personas "
            "need real numbers to analyze."
        )
        st.stop()

    metrics = assemble_metrics(
        fundamentals,
        history["Close"],
        dividends,
        macro,
        dividend_prices=dividend_prices if len(dividend_prices) else None,
    )
    user_prompt = build_prompt(ticker, metrics)
    results = []
    for name in selected:
        try:
            with st.spinner(f"{name} is thinking..."):
                reply = openrouter_client.ask(PERSONAS[name], user_prompt)
            verdict, conviction = parse_verdict(reply)
            results.append(
                {
                    "persona": name,
                    "reply": reply,
                    "verdict": verdict,
                    "conviction": conviction,
                    "error": None,
                }
            )
        except openrouter_client.OpenRouterError as exc:
            results.append(
                {
                    "persona": name,
                    "reply": None,
                    "verdict": None,
                    "conviction": None,
                    "error": str(exc),
                }
            )
    db.save_agent_run(ticker, user_prompt, results)

saved = db.latest_agent_run(ticker) if ticker else None
if not saved:
    st.stop()

st.caption(f"Saved run · {saved['created_at']}")
_show_comparison(saved["results"])
_show_replacements(ticker, provider, saved["results"])
with st.expander("Numbers given to the personas", expanded=False):
    st.code(saved["prompt"])
st.caption(
    f"Base DCF uses {DCF_GROWTH:.0%} growth and a {DCF_DISCOUNT:.0%} discount rate. "
    f"The slow-growth case uses {DCF_SLOW_GROWTH:.0%} growth and a "
    f"{DCF_STRESS_DISCOUNT:.0%} discount rate. Both run {DCF_YEARS} years and "
    f"then {DCF_TERMINAL_GROWTH:.1%} terminal growth."
)
for result in saved["results"]:
    name = result["persona"]
    profile = PROFILE_BY_NAME.get(name)
    st.subheader(name)
    if profile is not None:
        st.caption(f"{profile.group} · {profile.summary}")
    if result.get("error"):
        st.error(result["error"])
    elif result.get("reply"):
        st.markdown(result["reply"])

