from agents import explainer


def test_prompt_includes_only_the_facts_we_have():
    prompt = explainer.build_prompt("IVV", {"name": "iShares Core S&P 500 ETF", "kind": "ETF"})
    assert "Name: iShares Core S&P 500 ETF" in prompt
    assert "Type: ETF" in prompt
    assert "Sector:" not in prompt


def test_fallback_prefers_the_source_description():
    assert explainer.fallback_text("IVV", {"summary": "Tracks the S&P 500."}) == "Tracks the S&P 500."


def test_fallback_without_a_description_names_the_ticker():
    text = explainer.fallback_text("IVV", {"name": "iShares Core S&P 500 ETF", "kind": "ETF"})
    assert text == "iShares Core S&P 500 ETF (IVV) is an ETF."
    assert explainer.fallback_text("AAPL", {"name": "Apple Inc.", "kind": "Stock"}) == "Apple Inc. (AAPL) is a stock."
