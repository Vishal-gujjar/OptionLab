import csv
import gzip
import tempfile
import unittest

from pathlib import Path

from web.services.contract_metadata import (
    OUTPUT_FIELDS,
    import_nse_contract_file,
    normalize_contract_rows,
    parse_source_file_date
)


class TestContractMetadata(unittest.TestCase):

    def setUp(self):
        self.source_date = "2026-11-20"

        self.call_row = {
            "FinInstrmId": "126008",
            "UndrlygFinInstrmId": "26009",
            "FinInstrmNm": "OPTSTK",
            "TckrSymb": "RELIANCE",
            "XpryDt": "1483021800",
            "StrkPric": "140000",
            "OptnTp": "CE",
            "PrtdToTrad": "1",
            "MinLot": "500",
            "NewBrdLotQty": "500",
            "BidIntrvl": "5",
            "DelFlg": "N",
            "TradgStsNrmlMkt": "2",
            "ElgbltyNrmlMkt": "1",
            "OptnExrcStyle": "E",
            "CorpAdjstmnt": "N"
        }

        self.put_row = self.call_row.copy()
        self.put_row.update({
            "FinInstrmId": "126009",
            "OptnTp": "PE"
        })

    def test_only_stock_options_are_imported(self):
        index_row = self.call_row.copy()
        index_row["FinInstrmNm"] = "OPTIDX"
        index_row["TckrSymb"] = "NIFTY"

        result = normalize_contract_rows(
            [self.call_row, index_row],
            self.source_date
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["instrument_type"],
            "OPTSTK"
        )

    def test_expiry_timestamp_conversion(self):
        result = normalize_contract_rows(
            [self.call_row],
            self.source_date
        )

        self.assertEqual(
            result[0]["expiry_date"],
            "2026-12-29"
        )

    def test_strike_price_converted_from_paise(self):
        result = normalize_contract_rows(
            [self.call_row],
            self.source_date
        )

        self.assertEqual(
            result[0]["strike_price"],
            "1400.00"
        )

    def test_call_and_put_mapping(self):
        result = normalize_contract_rows(
            [self.call_row, self.put_row],
            self.source_date
        )

        self.assertEqual(
            result[0]["option_type"],
            "call"
        )

        self.assertEqual(
            result[1]["option_type"],
            "put"
        )

        self.assertEqual(
            result[0]["exchange_option_type"],
            "CE"
        )

        self.assertEqual(
            result[1]["exchange_option_type"],
            "PE"
        )

    def test_lot_size_fields_are_preserved(self):
        result = normalize_contract_rows(
            [self.call_row],
            self.source_date
        )

        self.assertEqual(
            result[0]["min_lot_quantity"],
            500
        )

        self.assertEqual(
            result[0]["board_lot_quantity"],
            500
        )

    def test_tick_size_conversion(self):
        result = normalize_contract_rows(
            [self.call_row],
            self.source_date
        )

        self.assertEqual(
            result[0]["tick_size"],
            "0.05"
        )

    def test_trading_and_deletion_flags(self):
        permitted = normalize_contract_rows(
            [self.call_row],
            self.source_date
        )[0]

        self.assertTrue(
            permitted["permitted_to_trade"]
        )

        self.assertFalse(
            permitted["is_deleted"]
        )

        self.assertTrue(
            permitted["normal_market_eligible"]
        )

        not_permitted_row = self.call_row.copy()
        not_permitted_row["PrtdToTrad"] = "0"

        not_permitted = normalize_contract_rows(
            [not_permitted_row],
            self.source_date
        )[0]

        self.assertFalse(
            not_permitted["permitted_to_trade"]
        )

    def test_deleted_contract_is_preserved_as_deleted(self):
        row = self.call_row.copy()
        row["DelFlg"] = "Y"

        result = normalize_contract_rows(
            [row],
            self.source_date
        )

        self.assertTrue(result[0]["is_deleted"])

    def test_invalid_option_type_is_rejected(self):
        row = self.call_row.copy()
        row["OptnTp"] = "XX"

        with self.assertRaises(ValueError):
            normalize_contract_rows(
                [row],
                self.source_date
            )

    def test_duplicate_contract_id_is_rejected(self):
        duplicate = self.call_row.copy()

        with self.assertRaises(ValueError):
            normalize_contract_rows(
                [self.call_row, duplicate],
                self.source_date
            )

    def test_empty_stock_option_data_is_rejected(self):
        index_row = self.call_row.copy()
        index_row["FinInstrmNm"] = "OPTIDX"

        with self.assertRaises(ValueError):
            normalize_contract_rows(
                [index_row],
                self.source_date
            )

    def test_contract_filename_date(self):
        with tempfile.TemporaryDirectory() as directory:

            path = Path(directory) / (
                "NSE_FO_contract_20112026.csv.gz"
            )

            self.assertEqual(
                parse_source_file_date(path),
                "2026-11-20"
            )

    def test_import_creates_normalized_csv(self):
        with tempfile.TemporaryDirectory() as directory:

            source_path = Path(directory) / (
                "NSE_FO_contract_20112026.csv.gz"
            )

            output_path = (
                Path(directory) / "nse_stock_options.csv"
            )

            headers = list(self.call_row.keys())

            with gzip.open(
                source_path,
                "wt",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=headers
                )

                writer.writeheader()
                writer.writerow(self.call_row)
                writer.writerow(self.put_row)

            result = import_nse_contract_file(
                file_path=source_path,
                output_path=output_path
            )

            self.assertTrue(output_path.exists())

            self.assertEqual(
                result["total_stock_option_contracts"],
                2
            )

            with output_path.open(
                "r",
                encoding="utf-8",
                newline=""
            ) as file:

                reader = csv.DictReader(file)
                rows = list(reader)

            self.assertEqual(len(rows), 2)
            self.assertEqual(
                rows[0]["strike_price"],
                "1400.00"
            )

            self.assertEqual(
                reader.fieldnames,
                OUTPUT_FIELDS
            )


if __name__ == "__main__":
    unittest.main()



    