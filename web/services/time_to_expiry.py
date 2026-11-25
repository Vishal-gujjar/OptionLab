from datetime import date, datetime


DAY_COUNT_BASIS = 365.0
DAY_COUNT_CONVENTION = "ACT/365F"


def _parse_date(value, field_name):
    """
    Accept a date, datetime, or ISO string in YYYY-MM-DD format.
    """

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a date in YYYY-MM-DD format."
        )

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()

    except ValueError as exc:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from exc


def calculate_time_to_expiry(valuation_date, expiry_date):
    """
    Calculate time to expiry using ACT/365 Fixed.

    Valuation date:
        Date of the cached underlying spot price.

    Expiry date:
        Actual listed option contract expiry date.

    Returns:
        Valuation date, expiry date, calendar days,
        day-count convention and year fraction.
    """

    valuation = _parse_date(
        valuation_date,
        "valuation_date"
    )

    expiry = _parse_date(
        expiry_date,
        "expiry_date"
    )

    calendar_days = (expiry - valuation).days

    if calendar_days <= 0:
        raise ValueError(
            f"Expiry date must be later than valuation date "
            f"({valuation.isoformat()})."
        )

    time_to_expiry_years = (
        calendar_days / DAY_COUNT_BASIS
    )

    return {
        "valuation_date": valuation.isoformat(),
        "expiry_date": expiry.isoformat(),
        "calendar_days_to_expiry": calendar_days,
        "day_count_convention": DAY_COUNT_CONVENTION,
        "time_to_expiry_years": time_to_expiry_years
    }



