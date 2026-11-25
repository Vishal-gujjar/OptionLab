import json
import math
import re
import os

from dotenv import load_dotenv
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from pathlib import Path

API_BASE_URL = "https://api.tejhq.dev"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

def fetch_ohlcv(
    symbol: str,
    start_date: str,
    end_date: str,
    exchange: str = "nse",
    timeout: int = 30
) -> dict:
    """
    Fetch historical end-of-day OHLCV data from TejHQ.

    Authentication is not required for this endpoint.

    Returns:
        {
            "meta": {...},
            "data": [...]
        }
    """

    # Validate exchange
    exchange = exchange.lower()

    if exchange not in ("nse", "bse"):
        raise ValueError("Exchange must be NSE or BSE.")

    # Validate symbol
    symbol = symbol.upper().strip()

    if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-&]{0,29}", symbol):
        raise ValueError("Invalid stock symbol.")

    # Validate dates
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

    except ValueError:
        raise ValueError(
            "Dates must use YYYY-MM-DD format."
        ) from None

    if start > end:
        raise ValueError("Start date cannot exceed end date.")

    # Prepare API URL
    query_parameters = urlencode({
        "from": start.isoformat(),
        "to": end.isoformat()
    })

    url = (
        f"{API_BASE_URL}/v1/ohlcv/"
        f"{exchange}/{symbol}?{query_parameters}"
    )

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "OptionLab/0.1"
        }
    )

    # Send HTTP request
    try:

        with urlopen(request, timeout=timeout) as response:

            status_code = response.status
            response_body = response.read().decode("utf-8")

    except HTTPError as error:

        body = error.read().decode("utf-8", errors="replace")

        raise RuntimeError(
            f"TejHQ HTTP error {error.code}: {body[:500]}"
        ) from None

    except URLError as error:

        raise ConnectionError(
            f"Could not connect to TejHQ: {error.reason}"
        ) from None

    if status_code != 200:
        raise RuntimeError(
            f"Unexpected HTTP status: {status_code}"
        )

    # Parse JSON
    try:
        payload = json.loads(response_body)

    except json.JSONDecodeError:
        raise RuntimeError(
            "TejHQ returned invalid JSON."
        ) from None

    # Validate API response
    if not isinstance(payload, dict):
        raise RuntimeError("Invalid API response structure.")

    rows = payload.get("data")

    if not isinstance(rows, list):
        raise RuntimeError("Missing OHLCV data.")

    metadata = payload.get("meta", {})

    # Validate returned price rows
    required_fields = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for row in rows:

        if not isinstance(row, dict):
            raise RuntimeError("Invalid OHLCV row.")

        if any(field not in row for field in required_fields):
            raise RuntimeError("Incomplete OHLCV row.")

        try:
            date.fromisoformat(row["date"])
        except (ValueError, TypeError):
            raise RuntimeError("Invalid date in OHLCV data.") from None

        prices = [
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            row["volume"]
        ]

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in prices
        ):
            raise RuntimeError("Invalid numerical market data.")

        if (
            min(prices[:4]) <= 0
            or row["volume"] < 0
            or row["high"] < row["low"]
            or row["high"] < max(row["open"], row["close"])
            or row["low"] > min(row["open"], row["close"])
        ):
            raise RuntimeError("Inconsistent OHLCV values.")

    # Sort oldest to newest
    rows.sort(key=lambda row: row["date"])

    return {
        "meta": metadata,
        "data": rows
    }



def fetch_adjusted(
    symbol: str,
    start_date: str,
    end_date: str,
    exchange: str = "nse",
    timeout: int = 30
) -> dict:
    """
    Fetch corporate-action-adjusted OHLCV data.

    Requires a free TejHQ API key.

    Adjusted close accounts for splits, bonuses and dividends.
    """

    import math

    exchange = exchange.lower()
    symbol = symbol.upper().strip()

    if exchange not in ("nse", "bse"):
        raise ValueError("Exchange must be NSE or BSE.")

    if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-&]{0,29}", symbol):
        raise ValueError("Invalid stock symbol.")

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise ValueError("Dates must use YYYY-MM-DD.") from None

    if start > end:
        raise ValueError("Invalid date range.")

    api_key = os.getenv("TEJHQ_API_KEY")

    if not api_key:
        raise ValueError(
            "TEJHQ_API_KEY is missing. Check your .env file."
        )

    query = urlencode({
        "from": start.isoformat(),
        "to": end.isoformat()
    })

    url = (
        f"{API_BASE_URL}/v1/adjusted/"
        f"{exchange}/{symbol}?{query}"
    )

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "OptionLab/0.1"
        }
    )

    try:

        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as error:

        body = error.read().decode(
            "utf-8", errors="replace"
        )

        raise RuntimeError(
            f"TejHQ adjusted API HTTP {error.code}: {body[:500]}"
        ) from None

    except URLError as error:

        raise ConnectionError(
            f"Could not connect to TejHQ: {error.reason}"
        ) from None

    except json.JSONDecodeError:
        raise RuntimeError(
            "TejHQ returned invalid JSON."
        ) from None

    if not isinstance(payload, dict):
        raise RuntimeError("Invalid adjusted API response.")

    rows = payload.get("data")

    if not isinstance(rows, list):
        raise RuntimeError("Adjusted price data is missing.")

    required_fields = [
        "date", "open", "high", "low", "close",
        "volume", "adj_factor_cumulative", "adj_close"
    ]

    for row in rows:

        if not isinstance(row, dict):
            raise RuntimeError("Invalid adjusted data row.")

        if any(field not in row for field in required_fields):
            raise RuntimeError("Incomplete adjusted data row.")

        try:
            date.fromisoformat(row["date"])
        except (ValueError, TypeError):
            raise RuntimeError("Invalid date in adjusted data.") from None

        numeric_fields = required_fields[1:]

        for field in numeric_fields:

            value = row[field]

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise RuntimeError(
                    f"Invalid adjusted value: {field}"
                )

        if (
            min(row["open"], row["high"],
                row["low"], row["close"], row["adj_close"]) <= 0
            or row["volume"] < 0
            or not float(row["volume"]).is_integer()
            or row["adj_factor_cumulative"] <= 0
            or row["high"] < max(row["open"], row["close"])
            or row["low"] > min(row["open"], row["close"])
        ):
            raise RuntimeError("Inconsistent adjusted price data.")

    rows.sort(key=lambda row: row["date"])

    return {
        "meta": payload.get("meta", {}),
        "data": rows
    }