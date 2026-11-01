"""The investor personas section, shared by the dashboard and the Agents page."""

import logging
import random
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

import pandas as pd
import streamlit as st

from agents import openrouter_client
from agents.metrics import assemble_metrics
from agents.personas import PERSONAS, PROFILE_BY_NAME, build_prompt, profiles_by_group
from agents.recommendations import CANDIDATES, pick_replacements, slammed
from agents.verdicts import parse_verdict, without_verdict
from config import (
    DCF_DISCOUNT,
    DCF_GROWTH,
    DCF_SLOW_GROWTH,
    DCF_STRESS_DISCOUNT,
    DCF_TERMINAL_GROWTH,
    DCF_YEARS,
)
from data import DataSourceError, cache, yahoo
from formatting import escape_dollars
from storage import db

logger = logging.getLogger(__name__)

_MAX_PARALLEL_ASKS = 8
_NETWORK_BUSY = "The network is busy right now. Please try again in a few minutes."
_JOKES = [
    "Why did the investor bring a ladder to work? They heard the market was reaching new highs.",
    "What's the difference between a bond and a bond trader? A bond eventually matures.",
    "Why don't bears get invited to parties? They always expect things to go down.",
    "I asked my broker for a stock that would let me sleep at night. They sold me a mattress company.",
    "My long-term investing plan is simple: buy low, then check my account a lot less often.",
]


def metrics_for(ticker: str, fundamentals: dict, closes: pd.Series, provider: str) -> dict:
    """Every number the personas and the key-numbers section read."""
    return assemble_metrics(
        fundamentals,
        closes,
        cache.get_dividends(ticker),
        cache.get_macro(),
        dividend_prices=_raw_closes(ticker, provider),
    )


def _raw_closes(symbol: str, provider: str) -> pd.Series | None:
    """Unadjusted closes for yield history, or None when they can't be fetched."""
    try:
        return cache.get_history(symbol, "5y", provider=provider, adjusted=False)["Close"]
    except DataSourceError:
        return None


def show_profiles() -> None:
    with st.expander("Who these personas are"):
        for group, profiles in profiles_by_group():
            st.markdown(f"**{group}**")
            for profile in profiles:
                st.markdown(f"**{profile.name}** — {profile.summary}")


def render(ticker: str, metrics: dict, quote: dict) -> None:
    st.subheader("What the investors would say")
    st.caption(
        "Inspired by how famous investors think. These aren't the real people, "
        "and this isn't financial advice."
    )
    show_profiles()
    selected = st.multiselect(
        "Choose your investors",
        [profile.name for _, profiles in profiles_by_group() for profile in profiles],
        format_func=_picker_label,
        placeholder="Choose one or more",
        key=f"personas_{ticker}",
    )
    # Answers belong to this viewer's current ticker, so every ticker starts blank.
    if st.session_state.get("persona_run", {}).get("ticker") != ticker:
        st.session_state.pop("persona_run", None)
    if st.button(f"Ask them about {ticker}", type="primary", disabled=not selected):
        _run(ticker, metrics, selected)

    if "persona_run" in st.session_state:
        _show_run(ticker, st.session_state["persona_run"], quote)


def _picker_label(name: str) -> str:
    return f"{name} · {PROFILE_BY_NAME[name].group}"


def _run(ticker: str, metrics: dict, names: list[str]) -> None:
    prompt = build_prompt(ticker, metrics)
    replies = {}
    last_try = threading.Event()
    # The toast shows wherever the viewer has scrolled to.
    st.toast(f"Asking {len(names)} about {ticker}...", icon="⏳")
    with st.status(f"Asking about {ticker}. This can take a few minutes...", expanded=True) as status:
        lines = {name: st.empty() for name in names}
        for name, line in lines.items():
            line.markdown(f"⏳ {name} is reading the numbers...")
        joke = st.empty()
        joke_told = False
        # Workers call only pure agent code, and each ask ends at its own deadline.
        with ThreadPoolExecutor(max_workers=_MAX_PARALLEL_ASKS) as pool:
            futures = {pool.submit(_ask, name, prompt, last_try.set): name for name in names}
            pending = set(futures)
            while pending:
                finished, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                for future in finished:
                    name = futures[future]
                    replies[name] = future.result()
                    lines[name].markdown(
                        f"✅ {name} has answered" if replies[name]["reply"]
                        else f"⚠️ {name}: the network is busy"
                    )
                    status.update(label=f"{len(replies)} of {len(names)} answered...", expanded=True)
                if last_try.is_set() and not joke_told:
                    joke_told = True
                    joke.info(f"This is taking a while, so here's a joke:\n\n{random.choice(_JOKES)}")
        answered = sum(1 for result in replies.values() if result["reply"])
        status.update(
            label=f"{answered} of {len(names)} answered",
            state="complete" if answered else "error",
            expanded=not answered,
        )
    if answered:
        results = [replies[name] for name in names]
        db.save_agent_run(ticker, prompt, results)
        st.session_state["persona_run"] = {"ticker": ticker, "prompt": prompt, "results": results}
        st.toast(f"{answered} of {len(names)} answered", icon="✅")
    else:
        st.error(_NETWORK_BUSY)


def _ask(name: str, prompt: str, on_last_try: Callable[[], None]) -> dict:
    try:
        reply = openrouter_client.ask(PERSONAS[name], prompt, on_last_try=on_last_try)
    except openrouter_client.OpenRouterError as exc:
        logger.warning("Persona %s failed: %s", name, exc)
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
                "How sure (1-10)": "—" if result.get("conviction") is None else str(result["conviction"]),
            }
            for result in results
        ),
        hide_index=True,
        width="stretch",
    )
    for result in results:
        name = result["persona"]
        label = f"{name}: {result.get('verdict') or 'no verdict'}"
        with st.expander(label):
            profile = PROFILE_BY_NAME.get(name)
            if profile is not None:
                st.caption(f"{profile.group} · {profile.summary}")
            if result.get("reply"):
                st.markdown(escape_dollars(without_verdict(result["reply"])))
            else:
                st.error("The network was busy, so this investor could not answer.")
    with st.expander("Numbers given to the personas"):
        st.code(saved["prompt"])
        st.caption(
            f"Base DCF uses {DCF_GROWTH:.0%} growth and a {DCF_DISCOUNT:.0%} discount rate. "
            f"The slow-growth case uses {DCF_SLOW_GROWTH:.0%} growth and a "
            f"{DCF_STRESS_DISCOUNT:.0%} discount rate. Both run {DCF_YEARS} years and "
            f"then {DCF_TERMINAL_GROWTH:.1%} terminal growth."
        )
    _show_replacements(ticker, results, quote)


def _show_replacements(ticker: str, results: list[dict], quote: dict) -> None:
    # Only prices are needed here, so skip the slower full-company sources.
    fetched = cache.get_snapshots(tuple(sorted(CANDIDATES)), yahoo.SOURCE_FALLBACK)
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
