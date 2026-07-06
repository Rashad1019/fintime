from analytics.ratios import (
    debt_to_equity,
    pb_ratio,
    pe_ratio,
    profit_margin,
    roe,
)


def test_pe_ratio_basic():
    assert pe_ratio(price=100.0, eps=5.0) == 20.0


def test_pe_ratio_zero_eps_returns_none():
    assert pe_ratio(price=100.0, eps=0.0) is None


def test_pe_ratio_negative_eps_returns_none():
    assert pe_ratio(price=100.0, eps=-2.0) is None


def test_pb_ratio_basic():
    assert pb_ratio(price=50.0, book_value_per_share=25.0) == 2.0


def test_pb_ratio_zero_book_value_returns_none():
    assert pb_ratio(price=50.0, book_value_per_share=0.0) is None


def test_roe_basic():
    assert roe(net_income=10.0, shareholder_equity=100.0) == 0.10


def test_roe_zero_equity_returns_none():
    assert roe(net_income=10.0, shareholder_equity=0.0) is None


def test_debt_to_equity_basic():
    assert debt_to_equity(total_debt=50.0, shareholder_equity=100.0) == 0.5


def test_debt_to_equity_zero_equity_returns_none():
    assert debt_to_equity(total_debt=50.0, shareholder_equity=0.0) is None


def test_profit_margin_basic():
    assert profit_margin(net_income=20.0, revenue=100.0) == 0.2


def test_profit_margin_zero_revenue_returns_none():
    assert profit_margin(net_income=20.0, revenue=0.0) is None


def test_none_inputs_return_none():
    assert pe_ratio(price=None, eps=5.0) is None
    assert pb_ratio(price=None, book_value_per_share=5.0) is None
    assert roe(net_income=None, shareholder_equity=100.0) is None
    assert debt_to_equity(total_debt=None, shareholder_equity=100.0) is None
    assert profit_margin(net_income=None, revenue=100.0) is None
