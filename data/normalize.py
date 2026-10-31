"""Small numeric cleanups shared by the data sources."""


def growth_fraction(value) -> float | None:
    """Return a growth rate as a fraction.

    Sources disagree on units: 0.15 and 15 both mean 15%. Values whose
    absolute size is above 2 are treated as percentage points.
    """
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if abs(number) > 2:
        number = number / 100
    return number
