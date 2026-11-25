import csv

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


from web.services.contract_metadata import (
    DEFAULT_OUTPUT_PATH,
    OUTPUT_FIELDS
)


def _parse_date(value, field_name):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a valid YYYY-MM-DD date."
        )


def _parse_symbol(symbol):
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("Symbol is required.")

    return symbol.strip().upper()


def _parse_option_type(option_type):
    value = str(option_type).strip().lower()

    if value not in ("call", "put"):
        raise ValueError(
            "Option type must be 'call' or 'put'."
        )

    return value


def _parse_strike(strike_price):
    if isinstance(strike_price, bool):
        raise ValueError("Strike price must be numeric.")

    try:
        strike = Decimal(str(strike_price))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Strike price must be numeric.")

    if not strike.is_finite() or strike <= 0:
        raise ValueError("Strike price must be positive.")

    return strike


def _parse_boolean(value, field_name):
    value = str(value).strip().lower()

    if value == "true":
        return True

    if value == "false":
        return False

    raise ValueError(
        f"Invalid Boolean value for {field_name}."
    )


def load_contracts(csv_path=None):
    """
    Load the normalized NSE stock-option contract master.
    """

    path = (
        Path(csv_path)
        if csv_path is not None
        else DEFAULT_OUTPUT_PATH
    )

    if not path.is_file():
        raise FileNotFoundError(
            f"Normalized contract file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(
                "Contract metadata CSV has no header."
            )

        missing = set(OUTPUT_FIELDS) - set(reader.fieldnames)

        if missing:
            raise ValueError(
                "Contract metadata CSV is missing fields: "
                + ", ".join(sorted(missing))
            )

        contracts = []

        for row_number, row in enumerate(reader, start=2):

            try:
                contract = dict(row)

                contract["symbol"] = _parse_symbol(
                    row["symbol"]
                )

                contract["expiry_date"] = _parse_date(
                    row["expiry_date"],
                    "expiry_date"
                ).isoformat()

                contract["strike_price"] = _parse_strike(
                    row["strike_price"]
                )

                contract["min_lot_quantity"] = int(
                    row["min_lot_quantity"]
                )

                contract["board_lot_quantity"] = int(
                    row["board_lot_quantity"]
                )

                contract["permitted_to_trade"] = (
                    _parse_boolean(
                        row["permitted_to_trade"],
                        "permitted_to_trade"
                    )
                )

                contract["is_deleted"] = _parse_boolean(
                    row["is_deleted"],
                    "is_deleted"
                )

                contract["normal_market_eligible"] = (
                    _parse_boolean(
                        row["normal_market_eligible"],
                        "normal_market_eligible"
                    )
                )

                if contract["min_lot_quantity"] <= 0:
                    raise ValueError("Minimum lot must be positive.")

                if contract["board_lot_quantity"] <= 0:
                    raise ValueError("Board lot must be positive.")

                contracts.append(contract)

            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Invalid normalized contract row "
                    f"{row_number}: {exc}"
                ) from exc

    if not contracts:
        raise ValueError(
            "Normalized contract master contains no records."
        )

    return contracts


def get_available_symbols(
    reference_date=None,
    csv_path=None
):
    """
    Return symbols having at least one non-deleted
    contract expiring after the reference date.

    Trading permission is returned separately in contract
    records; it is not used to silently remove contracts.
    """

    contracts = load_contracts(csv_path)

    if reference_date is not None:
        reference = _parse_date(
            reference_date,
            "reference_date"
        )
    else:
        reference = None

    symbols = set()

    for contract in contracts:

        if contract["is_deleted"]:
            continue

        expiry = date.fromisoformat(
            contract["expiry_date"]
        )

        if reference is not None and expiry <= reference:
            continue

        symbols.add(contract["symbol"])

    return sorted(symbols)


def get_available_expiries(
    symbol,
    reference_date,
    csv_path=None
):
    """
    Return actual non-deleted NSE expiry dates for a stock.
    """

    normalized_symbol = _parse_symbol(symbol)

    reference = _parse_date(
        reference_date,
        "reference_date"
    )

    contracts = load_contracts(csv_path)

    expiries = set()

    for contract in contracts:

        if contract["symbol"] != normalized_symbol:
            continue

        if contract["is_deleted"]:
            continue

        expiry = date.fromisoformat(
            contract["expiry_date"]
        )

        if expiry > reference:
            expiries.add(expiry)

    return [
        item.isoformat()
        for item in sorted(expiries)
    ]


def get_available_strikes(
    symbol,
    expiry_date,
    option_type,
    reference_date=None,
    csv_path=None
):
    """
    Return listed strike prices for a stock, expiry,
    and option type.
    """

    normalized_symbol = _parse_symbol(symbol)

    normalized_option_type = _parse_option_type(
        option_type
    )

    expiry = _parse_date(
        expiry_date,
        "expiry_date"
    )

    if reference_date is not None:

        reference = _parse_date(
            reference_date,
            "reference_date"
        )

        if expiry <= reference:
            return []

    contracts = load_contracts(csv_path)

    strikes = set()

    for contract in contracts:

        if contract["symbol"] != normalized_symbol:
            continue

        if contract["expiry_date"] != expiry.isoformat():
            continue

        if contract["option_type"] != normalized_option_type:
            continue

        if contract["is_deleted"]:
            continue

        strikes.add(contract["strike_price"])

    return sorted(strikes)


def validate_option_contract(
    symbol,
    expiry_date,
    strike_price,
    option_type,
    reference_date=None,
    csv_path=None
):
    """
    Validate an exact option contract against the
    normalized NSE contract master.

    The validator checks that:
        - The underlying symbol exists.
        - The contract is not deleted.
        - The expiry is valid.
        - The strike is actually listed.
        - The option type matches.

    Trading permission is returned separately.

    A listed contract which is not marked permitted to
    trade can still be theoretically priced, but its
    trading-permission status must be disclosed.
    """

    normalized_symbol = _parse_symbol(symbol)

    normalized_option_type = _parse_option_type(
        option_type
    )

    expiry = _parse_date(
        expiry_date,
        "expiry_date"
    )

    strike = _parse_strike(strike_price)

    if reference_date is not None:

        reference = _parse_date(
            reference_date,
            "reference_date"
        )

        if expiry <= reference:
            raise ValueError(
                "Contract expiry must be later than "
                "the valuation date."
            )

    contracts = load_contracts(csv_path)

    matches = []

    for contract in contracts:

        if contract["symbol"] != normalized_symbol:
            continue

        if contract["expiry_date"] != expiry.isoformat():
            continue

        if contract["strike_price"] != strike:
            continue

        if contract["option_type"] != normalized_option_type:
            continue

        if contract["is_deleted"]:
            continue

        matches.append(contract)

    if not matches:
        raise ValueError(
            "The selected option contract was not found "
            "in the current NSE contract master."
        )

    if len(matches) > 1:
        raise ValueError(
            "Multiple matching contracts were found. "
            "Contract metadata needs investigation."
        )

    contract = matches[0]

    return {
        "valid": True,

        "contract_id": contract["contract_id"],

        "symbol": contract["symbol"],

        "expiry_date": contract["expiry_date"],

        "strike_price": float(
            contract["strike_price"]
        ),

        "option_type": contract["option_type"],

        "exchange_option_type":
            contract["exchange_option_type"],

        "min_lot_quantity":
            contract["min_lot_quantity"],

        "board_lot_quantity":
            contract["board_lot_quantity"],

        "tick_size": float(
            contract["tick_size"]
        ),

        "permitted_to_trade":
            contract["permitted_to_trade"],

        "is_deleted":
            contract["is_deleted"],

        "normal_market_status":
            contract["normal_market_status"],

        "normal_market_eligible":
            contract["normal_market_eligible"],

        "source_file_date":
            contract["source_file_date"]
    }



    