import csv
import math

from datetime import date, datetime, timezone
from pathlib import Path

from web.services.csv_store import (
    CSV_COLUMNS,
    ADJUSTED_CSV_COLUMNS
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_retrieved_at(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None


def _inspect_dataset(
    path,
    expected_columns,
    symbol,
    exchange,
    price_basis
):
    result = {
        "available": False,
        "valid": False,
        "start_date": None,
        "latest_date": None,
        "observations": 0,
        "last_retrieved_at_utc": None,
        "latest_close": None,
        "error": None
    }

    if not path.is_file():
        result["error"] = "File is missing."
        return result

    # File exists, so an invalid schema or unreadable file
    # should be classified as invalid, not simply missing.
    result["available"] = True

    try:

        with path.open(
            "r",
            encoding="utf-8",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            if reader.fieldnames != expected_columns:
                result["error"] = (
                    "Unexpected CSV schema."
                )
                return result

            rows = list(reader)

        if not rows:
            result["error"] = (
                "CSV contains no observations."
            )
            return result

        parsed_rows = []
        retrieval_times = []
        seen_dates = set()

        # Numerical columns required for both datasets.
        numeric_fields = [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        # Additional fields required for adjusted data.
        if price_basis == "adjusted_close":

            numeric_fields.extend([
                "adj_factor_cumulative",
                "adj_close"
            ])

        for row in rows:

            # Validate instrument identity and price basis.
            if (
                row.get("symbol") != symbol
                or row.get("exchange") != exchange.upper()
                or row.get("price_basis") != price_basis
            ):
                result["error"] = (
                    "Instrument or price-basis mismatch."
                )
                return result

            # Validate date.
            date_text = row.get("date")

            try:
                observation_date = date.fromisoformat(
                    date_text
                )

            except (ValueError, TypeError):
                result["error"] = (
                    "Invalid observation date."
                )
                return result

            if observation_date.isoformat() != date_text:
                result["error"] = (
                    "Observation date must use YYYY-MM-DD."
                )
                return result

            # Duplicate dates should not exist in the cache.
            if observation_date in seen_dates:
                result["error"] = (
                    "Duplicate observation dates found."
                )
                return result

            seen_dates.add(observation_date)

            # Parse every numerical field.
            try:

                values = {
                    field: float(row[field])
                    for field in numeric_fields
                }

            except (ValueError, TypeError, KeyError, OverflowError):

                result["error"] = (
                    "Invalid numerical market data."
                )
                return result

            # Reject NaN and positive/negative Infinity.
            if not all(
                math.isfinite(value)
                for value in values.values()
            ):
                result["error"] = (
                    "Market data contains NaN or Infinity."
                )
                return result

            # OHLC prices must be positive.
            if any(
                values[field] <= 0
                for field in (
                    "open",
                    "high",
                    "low",
                    "close"
                )
            ):
                result["error"] = (
                    "OHLC prices must be positive."
                )
                return result

            # Validate volume.
            volume = values["volume"]

            if volume < 0 or not volume.is_integer():
                result["error"] = (
                    "Volume must be a non-negative integer."
                )
                return result

            # Validate the high and low relationship.
            if (
                values["high"] < max(
                    values["open"],
                    values["close"],
                    values["low"]
                )
                or values["low"] > min(
                    values["open"],
                    values["close"],
                    values["high"]
                )
            ):
                result["error"] = (
                    "Inconsistent OHLC values."
                )
                return result

            # Extra adjusted-data checks.
            if price_basis == "adjusted_close":

                if (
                    values["adj_factor_cumulative"] <= 0
                    or values["adj_close"] <= 0
                ):
                    result["error"] = (
                        "Adjusted close and adjustment factor "
                        "must be positive."
                    )
                    return result

            parsed_rows.append((
                observation_date,
                row,
                values
            ))

            # Retrieval timestamp is metadata.
            retrieved = _parse_retrieved_at(
                row.get("retrieved_at_utc")
            )

            if retrieved is not None:
                retrieval_times.append(retrieved)

        dates = [
            item[0]
            for item in parsed_rows
        ]

        # CSV cache files should be chronological.
        if dates != sorted(dates):
            result["error"] = (
                "Market-data observations are not chronological."
            )
            return result

        latest_date, latest_row, latest_values = parsed_rows[-1]

        result.update({
            "available": True,
            "valid": True,

            "start_date": dates[0].isoformat(),
            "latest_date": latest_date.isoformat(),

            "observations": len(rows),

            "latest_close": latest_values["close"],

            "last_retrieved_at_utc": (
                max(retrieval_times).isoformat()
                if retrieval_times else None
            ),

            "error": None
        })

        return result

    except (OSError, UnicodeError, csv.Error) as exc:

        result["error"] = (
            f"Could not read CSV: {exc}"
        )

        return result


def get_market_data_status(
    symbol,
    exchange="nse",
    cache_dir=None,
    as_of_date=None,
    fresh_after_days=4,
    stale_after_days=7
):
    """
    Inspect raw and adjusted market-data caches.

    Freshness is a calendar-day warning heuristic.
    It is not an official NSE trading-calendar calculation.
    """

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("A stock symbol is required.")

    symbol = symbol.strip().upper()
    exchange = str(exchange).strip().lower()

    if exchange not in ("nse", "bse"):
        raise ValueError("Exchange must be NSE or BSE.")

    if (
        isinstance(fresh_after_days, bool)
        or not isinstance(fresh_after_days, int)
        or fresh_after_days < 0
    ):
        raise ValueError("fresh_after_days must be non-negative.")

    if (
        isinstance(stale_after_days, bool)
        or not isinstance(stale_after_days, int)
        or stale_after_days <= fresh_after_days
    ):
        raise ValueError(
            "stale_after_days must exceed fresh_after_days."
        )

    reference_date = (
        date.fromisoformat(as_of_date)
        if isinstance(as_of_date, str)
        else as_of_date
        if isinstance(as_of_date, date)
        else date.today()
    )

    data_dir = Path(
        cache_dir or PROJECT_ROOT / "data" / "cache"
    )

    raw_path = data_dir / f"{exchange}_{symbol}.csv"

    adjusted_path = (
        data_dir / f"{exchange}_{symbol}_adjusted.csv"
    )

    raw = _inspect_dataset(
        raw_path,
        CSV_COLUMNS,
        symbol,
        exchange,
        "raw_ohlcv"
    )

    adjusted = _inspect_dataset(
        adjusted_path,
        ADJUSTED_CSV_COLUMNS,
        symbol,
        exchange,
        "adjusted_close"
    )

    warnings = []

    raw_age = None
    adjusted_age = None

    # --------------------------------------------------
    # 1. Check raw dataset availability and validity
    # --------------------------------------------------

    if not raw["available"]:

        warnings.append(
            f"Raw OHLCV data unavailable: {raw['error']}"
        )

    elif not raw["valid"]:

        warnings.append(
            f"Raw OHLCV data invalid: {raw['error']}"
        )

    # --------------------------------------------------
    # 2. Check adjusted dataset availability and validity
    # --------------------------------------------------

    if not adjusted["available"]:

        warnings.append(
            f"Adjusted data unavailable: {adjusted['error']}"
        )

    elif not adjusted["valid"]:

        warnings.append(
            f"Adjusted data invalid: {adjusted['error']}"
        )

    # --------------------------------------------------
    # 3. Calculate raw-data age only when valid
    # --------------------------------------------------

    if (
        raw["available"]
        and raw["valid"]
        and raw["latest_date"] is not None
    ):

        raw_date = date.fromisoformat(
            raw["latest_date"]
        )

        raw_age = (
            reference_date - raw_date
        ).days

        if raw_age < 0:

            warnings.append(
                "Raw market data contains a date "
                "after the reference date."
            )

    # --------------------------------------------------
    # 4. Calculate adjusted-data age only when valid
    # --------------------------------------------------

    if (
        adjusted["available"]
        and adjusted["valid"]
        and adjusted["latest_date"] is not None
    ):

        adjusted_date = date.fromisoformat(
            adjusted["latest_date"]
        )

        adjusted_age = (
            reference_date - adjusted_date
        ).days

        if adjusted_age < 0:

            warnings.append(
                "Adjusted data contains a date "
                "after the reference date."
            )

    # --------------------------------------------------
    # 5. Compare latest dates only when both are valid
    # --------------------------------------------------

    dates_match = (
        raw["available"]
        and raw["valid"]
        and adjusted["available"]
        and adjusted["valid"]
        and raw["latest_date"] is not None
        and adjusted["latest_date"] is not None
        and raw["latest_date"] == adjusted["latest_date"]
    )

    if (
        raw["available"]
        and raw["valid"]
        and adjusted["available"]
        and adjusted["valid"]
        and not dates_match
    ):

        warnings.append(
            "Raw and adjusted datasets have different latest dates."
        )

    # --------------------------------------------------
    # 6. Calculate maximum dataset age
    # --------------------------------------------------

    ages = [
        age
        for age in (raw_age, adjusted_age)
        if age is not None
    ]

    maximum_age = (
        max(ages)
        if ages
        else None
    )

    # --------------------------------------------------
    # 7. Determine final data status
    # --------------------------------------------------

    if (
        not raw["available"]
        or not adjusted["available"]
    ):

        status = "missing"

    elif (
        not raw["valid"]
        or not adjusted["valid"]
    ):

        status = "invalid"

    elif (
        raw_age is None
        or adjusted_age is None
    ):

        status = "invalid"

        warnings.append(
            "Could not determine the age of both datasets."
        )

    elif raw_age < 0 or adjusted_age < 0:

        status = "invalid"

    elif not dates_match:

        status = "date_mismatch"

    elif maximum_age > stale_after_days:

        status = "stale"

        warnings.append(
            f"Market data is more than {stale_after_days} "
            "calendar days old."
        )

    elif maximum_age > fresh_after_days:

        status = "aging"

        warnings.append(
            "Market data is older than the preferred freshness window."
        )

    else:

        status = "fresh"

    # --------------------------------------------------
    # 8. Return complete status information
    # --------------------------------------------------

    return {
        "symbol": symbol,

        "exchange": exchange.upper(),

        "reference_date": reference_date.isoformat(),

        "status": status,

        "dates_match": dates_match,

        "raw_age_calendar_days": raw_age,

        "adjusted_age_calendar_days": adjusted_age,

        "raw": raw,

        "adjusted": adjusted,

        "warnings": warnings,

        "freshness_policy": {
            "fresh_through_calendar_days": fresh_after_days,

            "stale_after_calendar_days": stale_after_days,

            "basis": "Calendar-day heuristic, not exchange calendar"
        }
    }


