import pytest

from analytics.dcf import dcf_value


def test_dcf_one_year_hand_computed():
    # Year 1 FCF = 100 (no growth). PV = 100 / 1.1 = 90.909...
    # Terminal value = 100 / 0.10 = 1000, discounted = 1000 / 1.1 = 909.09...
    # Total = exactly 1000.
    value = dcf_value(
        fcf=100.0,
        growth_rate=0.0,
        discount_rate=0.10,
        terminal_growth=0.0,
        years=1,
    )
    assert value == pytest.approx(1000.0)


def test_dcf_two_years_hand_computed():
    # Year 1 = 105, Year 2 = 110.25
    # PV = 105/1.1 + 110.25/1.21 = 95.4545 + 91.1157 = 186.5702
    # TV = 110.25 * 1.02 / (0.10 - 0.02) = 1405.6875; PV(TV) = 1405.6875/1.21 = 1161.7252
    value = dcf_value(
        fcf=100.0,
        growth_rate=0.05,
        discount_rate=0.10,
        terminal_growth=0.02,
        years=2,
    )
    assert value == pytest.approx(1348.2955, rel=1e-4)


def test_dcf_discount_rate_must_exceed_terminal_growth():
    with pytest.raises(ValueError):
        dcf_value(
            fcf=100.0,
            growth_rate=0.05,
            discount_rate=0.03,
            terminal_growth=0.03,
            years=5,
        )


def test_dcf_years_must_be_positive():
    with pytest.raises(ValueError):
        dcf_value(
            fcf=100.0,
            growth_rate=0.0,
            discount_rate=0.10,
            terminal_growth=0.0,
            years=0,
        )


def test_dcf_negative_fcf_gives_negative_value():
    value = dcf_value(
        fcf=-100.0,
        growth_rate=0.0,
        discount_rate=0.10,
        terminal_growth=0.0,
        years=5,
    )
    assert value < 0
