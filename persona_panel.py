"""The investor personas section of the ticker page."""

import pandas as pd
import streamlit as st

from agents import openrouter_client
from agents.personas import PERSONAS, PROFILE_BY_NAME, build_prompt
from agents.recommendations import CANDIDATES, pick_replacements, slammed
from agents.verdicts import parse_verdict
from data import cache
from formatting import escape_dollars
from storage import db

# Each persona is a paid-for model call, so one click is capped.
MAX_PERSONAS = 4
_FUND_DEFAULTS = ["Rick Ferri", "Paul Merriman", "Dave Nadig", "Daniel Sotiroff"]
_STOCK_DEFAULTS = ["Warren Buffett", "Peter Lynch", "Cathie Wood", "Ian Dunlap"]


def render(ticker: str, metrics: dict, quote: dict, is_fund: bool) -> None:
    st.subheader("What the investors would say")
    st.caption(
        "AI personas modeled on how famous investors think, each given the "
        "real numbers above. These are not the actual people, and this is "
        "not financial advice."
    )
    selected = st.multiselect(
        f"Pick up to {MAX_PERSONAS}",
        list(PERSONAS),
        default=_FUND_DEFAULTS if is_fund else _STOCK_DEFAULTS,
        max_selections=MAX_PERSONAS,
        key=f"personas_{'fund' if is_fund else 'stock'}",
    )
    if st.button(f"Ask them about {ticker}", type="primary", disabled=not selected):
        _run(ticker, metrics, selected)

    saved = db.latest_agent_run(ticker)
    if saved:
        _show_run(ticker, saved, quote)


def _run(ticker: str, metrics: dict, names: list[str]) -> None:
    prompt = build_prompt(ticker, metrics)
    results = []
    for name in names:
        with st.spinner(f"{name} is thinking..."):
            results.append(_ask(name, prompt))
    if any(result["reply"] for result in results):
        db.save_agent_run(ticker, prompt, results)
    else:
        st.error("The investors could not be reached right now. Try again in a minute.")


def _ask(name: str, prompt: str) -> dict:
    try:
        reply = openrouter_client.ask(PERSONAS[name], prompt)
    except openrouter_client.OpenRouterError as exc:
        return {"persona": name, "reply": None, "verdict": None, "conviction": None, "error": str(exc)}
    verdict, conviction = parse_verdict(reply)
    return {"persona": name, "reply": reply, "verdict": verdict, "conviction": conviction, "error": None}


def _show_run(ticker: str, saved: dict, quote: dict) -> None:
    results = saved["results"]
    st.dataframe(
        pd.DataFrame(
            {
                "Investor": result["persona"],
                "Verdict": result.get("verdict") or "—",
                "Conviction (1-10)": "—" if result.get("conviction") is None else result["conviction"],
            }
            for result in results
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(f"Last asked {saved['created_at']} UTC")
    for result in results:
        name = result["persona"]
        label = f"{name}: {result.get('verdict') or 'no verdict'}"
        with st.expander(label):
            profile = PROFILE_BY_NAME.get(name)
            if profile is not None:
                st.caption(profile.summary)
            if result.get("reply"):
                st.markdown(escape_dollars(result["reply"]))
            else:
                st.error("This investor could not be reached.")
    _show_replacements(ticker, results, quote)


def _show_replacements(ticker: str, results: list[dict], quote: dict) -> None:
    fetched = cache.get_snapshots(tuple(sorted(CANDIDATES)))
    quotes = {
        candidate: snapshot.get("quote")
        for candidate, snapshot in fetched.items()
        if snapshot and snapshot.get("quote")
    }
    picks = pick_replacements(ticker, quote.get("price"), quote.get("name"), quotes)
    if not picks:
        return
    st.subheader(f"Instead of {ticker}" if slammed(results) else f"Two ideas next to {ticker}")
    labels = {"role": "In its place", "price": "Close in price"}
    for column, pick in zip(st.columns(len(picks)), picks):
        column.markdown(f"**{labels[pick['slot']]} · {pick['ticker']}**")
        column.caption(escape_dollars(pick["reason"]))
