"""Discounted cash flow valuation as a pure function."""


def dcf_value(
    fcf: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float,
    years: int = 5,
) -> float:
    """Present value of projected free cash flows plus terminal value.

    fcf: most recent annual free cash flow.
    growth_rate: annual FCF growth during the projection window.
    discount_rate: required rate of return (must exceed terminal_growth).
    terminal_growth: perpetual growth after the projection window.
    years: projection window length.
    """
    if years < 1:
        raise ValueError("years must be at least 1")
    if discount_rate <= terminal_growth:
        raise ValueError("discount_rate must exceed terminal_growth")

    present_value = 0.0
    projected_fcf = fcf
    for year in range(1, years + 1):
        projected_fcf = projected_fcf * (1 + growth_rate)
        present_value += projected_fcf / (1 + discount_rate) ** year

    terminal_value = (
        projected_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    )
    present_value += terminal_value / (1 + discount_rate) ** years

    return present_value
