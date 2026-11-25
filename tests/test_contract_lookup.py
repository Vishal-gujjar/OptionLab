import csv
import tempfile
import unittest

from pathlib import Path

from web.services.contract_metadata import OUTPUT_FIELDS

from web.services.contract_lookup import (
    get_available_symbols,
    get_available_expiries,
    get_available_strikes,
    validate_option_contract
)


class TestContractLookup(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.csv_path = (
            Path(self.temp_dir.name) / "contracts.csv"
        )

        rows = [
            self.make_row(
                "1001", "RELIANCE",
                "2026-11-23", "1400.00",
                "call", "CE", True, False, 500
            ),

            self.make_row(
                "1002", "RELIANCE",
                "2026-11-23", "1400.00",
                "put", "PE", False, False, 500
            ),

            self.make_row(
                "1003", "RELIANCE",
                "2026-12-29", "1450.00",
                "call", "CE", True, False, 500
            ),

            self.make_row(
                "1004", "TCS",
                "2026-12-29", "2400.00",
                "call", "CE", True, False, 225
            ),

            self.make_row(
                "1005", "TCS",
                "2026-12-29", "2400.00",
                "put", "PE", True, True, 225
            ),

            self.make_row(
                "1006", "INFY",
                "2026-11-20", "1500.00",
                "call", "CE", True, False, 300
            )
        ]

        with self.csv_path.open(
            "w",
            encoding="utf-8",
            newline=""
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=OUTPUT_FIELDS
            )

            writer.writeheader()
            writer.writerows(rows)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def make_row(
        contract_id,
        symbol,
        expiry,
        strike,
        option_type,
        exchange_option_type,
        permitted,
        deleted,
        lot
    ):

        from datetime import datetime, timezone

        return {
            "contract_id": contract_id,
            "underlying_instrument_id": "123",
            "instrument_type": "OPTSTK",
            "symbol": symbol,
            "expiry_date": expiry,
            "strike_price": strike,
            "option_type": option_type,
            "exchange_option_type": exchange_option_type,
            "min_lot_quantity": str(lot),
            "board_lot_quantity": str(lot),
            "tick_size": "0.05",
            "permitted_to_trade": str(permitted),
            "is_deleted": str(deleted),
            "normal_market_status": "2",
            "normal_market_eligible": "True",
            "exercise_style": "E",
            "corporate_adjusted": "N",
            "source_file_date": "2026-11-20",
            "imported_at_utc": datetime.now(
                timezone.utc
            ).isoformat()
        }

    def test_available_symbols(self):
        result = get_available_symbols(
            "2026-11-20",
            self.csv_path
        )

        self.assertEqual(
            result,
            ["RELIANCE", "TCS"]
        )

    def test_expired_symbols_are_excluded(self):
        result = get_available_symbols(
            "2026-11-23",
            self.csv_path
        )

        self.assertNotIn("INFY", result)

    def test_available_expiries(self):
        result = get_available_expiries(
            "RELIANCE",
            "2026-11-20",
            self.csv_path
        )

        self.assertEqual(
            result,
            ["2026-11-23", "2026-12-29"]
        )

    def test_available_strikes_for_call(self):
        result = get_available_strikes(
            "RELIANCE",
            "2026-11-23",
            "call",
            "2026-11-20",
            self.csv_path
        )

        self.assertEqual(
            [float(x) for x in result],
            [1400.0]
        )

    def test_available_strikes_for_put(self):
        result = get_available_strikes(
            "RELIANCE",
            "2026-11-23",
            "put",
            "2026-11-20",
            self.csv_path
        )

        self.assertEqual(
            [float(x) for x in result],
            [1400.0]
        )

    def test_validate_call_contract(self):
        result = validate_option_contract(
            "RELIANCE",
            "2026-11-23",
            1400,
            "call",
            "2026-11-20",
            self.csv_path
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["contract_id"], "1001")
        self.assertEqual(result["option_type"], "call")
        self.assertTrue(result["permitted_to_trade"])
        self.assertEqual(result["board_lot_quantity"], 500)

    def test_validate_put_contract(self):
        result = validate_option_contract(
            "RELIANCE",
            "2026-11-23",
            1400,
            "put",
            "2026-11-20",
            self.csv_path
        )

        self.assertEqual(
            result["exchange_option_type"],
            "PE"
        )

        self.assertFalse(result["permitted_to_trade"])

    def test_deleted_contract_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_option_contract(
                "TCS",
                "2026-12-29",
                2400,
                "put",
                "2026-11-20",
                self.csv_path
            )

    def test_unlisted_strike_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_option_contract(
                "RELIANCE",
                "2026-11-23",
                1425,
                "call",
                "2026-11-20",
                self.csv_path
            )

    def test_invalid_symbol_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_option_contract(
                "UNKNOWN",
                "2026-12-29",
                1400,
                "call",
                "2026-11-20",
                self.csv_path
            )

    def test_expiry_on_or_before_valuation_date_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_option_contract(
                "RELIANCE",
                "2026-11-23",
                1400,
                "call",
                "2026-11-23",
                self.csv_path
            )


if __name__ == "__main__":
    unittest.main()