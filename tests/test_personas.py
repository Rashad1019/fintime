from agents.personas import PERSONAS, build_prompt

EXPECTED_PERSONAS = {
    "Warren Buffett",
    "Charlie Munger",
    "Benjamin Graham",
    "Peter Lynch",
    "Seth Klarman",
    "Howard Marks",
    "Phil Fisher",
    "Ray Dalio",
    "Michael Burry",
    "Cathie Wood",
    "Joel Greenblatt",
    "John Templeton",
    "Jack Bogle",
    "Geraldine Weiss",
    "Kevin O'Leary",
    "Masayoshi Son",
    "Marc Andreessen",
    "Chamath Palihapitiya",
    "Ian Dunlap",
    "Wall Street Trapper",
}

SAMPLE_METRICS = {
    "price": 150.0,
    "pe_ratio": 25.3,
    "pb_ratio": 8.1,
    "roe": 0.31,
    "debt_to_equity": 1.2,
    "profit_margin": 0.24,
    "dcf_value_per_share": 140.55,
}


def test_all_expected_personas_exist():
    assert EXPECTED_PERSONAS == set(PERSONAS.keys())


def test_every_persona_has_nonempty_system_prompt():
    for name, prompt in PERSONAS.items():
        assert isinstance(prompt, str)
        assert len(prompt) > 100, f"{name} system prompt looks too short"


def test_build_prompt_includes_ticker_and_metrics():
    prompt = build_prompt("AAPL", SAMPLE_METRICS)
    assert "AAPL" in prompt
    assert "25.3" in prompt
    assert "140.55" in prompt


def test_build_prompt_shows_na_for_missing_metrics():
    metrics = dict(SAMPLE_METRICS, pe_ratio=None)
    prompt = build_prompt("AAPL", metrics)
    assert "N/A" in prompt


def test_build_prompt_instructs_grounding_in_provided_numbers():
    prompt = build_prompt("MSFT", SAMPLE_METRICS)
    assert "only the numbers provided" in prompt.lower()


def test_build_prompt_renders_percent_metrics_as_percentages():
    metrics = {"dividend_yield": 0.0325, "roe": 0.31, "payout_ratio": 0.1259}
    prompt = build_prompt("SCHD", metrics)
    assert "3.25%" in prompt
    assert "31.00%" in prompt
    assert "12.59%" in prompt
