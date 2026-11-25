import unittest
from datetime import date

from web.services.time_to_expiry import calculate_time_to_expiry


class TimeToExpiryTests(unittest.TestCase):

    def test_four_calendar_days(self):

        result = calculate_time_to_expiry(
            "2026-11-20",
            "2026-11-24"
        )

        self.assertEqual(
            result["calendar_days_to_expiry"],
            4
        )

        self.assertAlmostEqual(
            result["time_to_expiry_years"],
            4 / 365
        )

        self.assertEqual(
            result["day_count_convention"],
            "ACT/365F"
        )

    def test_date_objects_are_supported(self):

        result = calculate_time_to_expiry(
            date(2026, 11, 20),
            date(2026, 11, 24)
        )

        self.assertEqual(
            result["calendar_days_to_expiry"],
            4
        )

    def test_leap_year_uses_fixed_365_denominator(self):

        result = calculate_time_to_expiry(
            "2028-02-28",
            "2028-03-01"
        )

        self.assertEqual(
            result["calendar_days_to_expiry"],
            2
        )

        self.assertAlmostEqual(
            result["time_to_expiry_years"],
            2 / 365
        )

    def test_same_date_is_rejected(self):

        with self.assertRaises(ValueError):
            calculate_time_to_expiry(
                "2026-11-20",
                "2026-11-20"
            )

    def test_past_expiry_is_rejected(self):

        with self.assertRaises(ValueError):
            calculate_time_to_expiry(
                "2026-11-20",
                "2026-11-19"
            )

    def test_invalid_date_format_is_rejected(self):

        with self.assertRaises(ValueError):
            calculate_time_to_expiry(
                "20-11-2026",
                "24-11-2026"
            )


if __name__ == "__main__":
    unittest.main()



    