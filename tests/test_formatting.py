from formatting import escape_dollars, fmt_money, fmt_pct, fmt_ratio


def test_escape_dollars_escapes_every_dollar_sign():
    assert escape_dollars("$371.57 vs $284.34") == r"\$371.57 vs \$284.34"
    assert escape_dollars("no money here") == "no money here"


def test_fmt_ratio_formats_with_two_decimals_and_thousands():
    assert fmt_ratio(25.3) == "25.30"
    assert fmt_ratio(1234.5) == "1,234.50"


def test_fmt_ratio_none_is_na():
    assert fmt_ratio(None) == "N/A"


def test_fmt_pct_converts_fraction_to_percent():
    assert fmt_pct(0.0325) == "3.25%"
    assert fmt_pct(0.31) == "31.00%"


def test_fmt_pct_none_is_na():
    assert fmt_pct(None) == "N/A"


def test_fmt_money_compacts_large_values():
    assert fmt_money(4.58e12) == "4.58T"
    assert fmt_money(84.71e9) == "84.71B"
    assert fmt_money(12.3e6) == "12.30M"


def test_fmt_money_small_values_and_none():
    assert fmt_money(999.5) == "999.50"
    assert fmt_money(None) == "N/A"


def test_fmt_money_negative_values_keep_suffix():
    assert fmt_money(-2.5e9) == "-2.50B"
