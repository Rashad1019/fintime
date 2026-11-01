"""The investor personas section, shared by the dashboard and the Agents page."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

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
)
from data import DataSourceError, cache, yahoo
from formatting import escape_dollars
from storage import db

logger = logging.getLogger(__name__)

_MAX_PARALLEL_ASKS = 8


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
        "AI personas modeled on how famous investors think, each given the "
        "real numbers on this page. These are not the actual people, and this "
        "is not financial advice."
    )
    show_profiles()
    selected = st.multiselect(
        "Choose your investors",
        [profile.name for _, profiles in profiles_by_group() for profile in profiles],
        format_func=_picker_label,
        placeholder="Choose one or more",
        key="personas",
    )
    if st.button(f"Ask them about {ticker}", type="primary", disabled=not selected):
        _run(ticker, metrics, selected)

    saved = db.latest_agent_run(ticker)
    if saved:
        _show_run(ticker, saved, quote)


def _picker_label(name: str) -> str:
    return f"{name} · {PROFILE_BY_NAME[name].group}"


def _run(ticker: str, metrics: dict, names: list[str]) -> None:
    prompt = build_prompt(ticker, metrics)
    replies = {}
    # The toast shows wherever the viewer has scrolled to.
    st.toast(f"Asking {len(names)} about {ticker}...", icon="⏳")
    with st.status(f"Asking about {ticker}. This can take a minute or two...", expanded=True) as status:
        lines = {name: st.empty() for name in names}
        for name, line in lines.items():
            line.markdown(f"⏳ {name} is reading the numbers...")
        # Workers call only pure agent code, and each ask ends at its own deadline.
        with ThreadPoolExecutor(max_workers=_MAX_PARALLEL_ASKS) as pool:
            futures = {pool.submit(_ask, name, prompt): name for name in names}
            for finished in as_completed(futures):
                name = futures[finished]
                replies[name] = finished.result()
                done = f"✅ {name} has answered" if replies[name]["reply"] else f"⚠️ {name} could not be reached"
                lines[name].markdown(done)
                status.update(label=f"{len(replies)} of {len(names)} answered...", expanded=True)
        answered = sum(1 for result in replies.values() if result["reply"])
        status.update(
            label=f"{answered} of {len(names)} answered",
            state="complete" if answered else "error",
            expanded=not answered,
        )
    if answered:
        db.save_agent_run(ticker, prompt, [replies[name] for name in names])
        st.toast(f"{answered} of {len(names)} answered", icon="✅")
    else:
        st.error("The investors could not be reached right now. Try again in a minute.")


def _ask(name: str, prompt: str) -> dict:
    try:
        reply = openrouter_client.ask(PERSONAS[name], prompt)
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
                "Conviction (1-10)": "—" if result.get("conviction") is None else str(result["conviction"]),
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
                st.caption(f"{profile.group} · {profile.summary}")
            if result.get("reply"):
                st.markdown(escape_dollars(result["reply"]))
            else:
                st.error("This investor could not be reached.")
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
