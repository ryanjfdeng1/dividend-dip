import unittest

import numpy as np
import pandas as pd

from indicators import calculate_metrics
from scanner import _has_usable_fundamentals, _normalize_data_status


class DataQualityStatusTests(unittest.TestCase):
    def test_unusable_sec_cache_cannot_remain_ok(self):
        row = {
            "fundamentals_available": False,
            "data_quality": "D",
            "data_status": "OK",
            "fundamentals_source": "SEC_CACHE",
        }
        self.assertEqual(_normalize_data_status(row)["data_status"], "INCOMPLETE")

    def test_nan_fundamentals_are_not_usable(self):
        row = {
            "fundamentals_available": True,
            "eps": float("nan"),
            "free_cash_flow": float("nan"),
            "revenue": float("nan"),
            "data_status": "OK",
        }
        self.assertFalse(_has_usable_fundamentals(row))

    def test_zero_is_a_valid_fundamental(self):
        row = {
            "fundamentals_available": True,
            "eps": 0.0,
            "data_status": "OK",
        }
        self.assertTrue(_has_usable_fundamentals(row))

    def test_fcf_payout_uses_total_dividend_cash(self):
        dates = pd.date_range("2025-09-01", periods=400, freq="D")
        history = pd.DataFrame({
            "Close": np.full(len(dates), 100.0),
            "Dividend": np.zeros(len(dates)),
        }, index=dates)
        for idx in [320, 230, 140, 50]:
            history.iloc[idx, history.columns.get_loc("Dividend")] = 1.25

        result = calculate_metrics(
            history,
            {
                "fundamentals_available": True,
                "eps": 10.0,
                "free_cash_flow": 10_000_000_000.0,
                "shares_outstanding": 1_000_000_000.0,
                "equity": 20_000_000_000.0,
                "debt": 5_000_000_000.0,
                "data_status": "OK",
                "data_quality": "A",
            },
        )
        self.assertAlmostEqual(result["fcf_payout_ratio"], 0.5, places=6)

    def test_stale_data_is_stale(self):
        row = {
            "fundamentals_available": False,
            "data_quality": "E",
            "data_status": "OK",
        }
        self.assertEqual(_normalize_data_status(row)["data_status"], "STALE")

    def test_sec_error_is_error(self):
        row = {
            "fundamentals_available": False,
            "data_quality": "E",
            "data_status": "OK",
            "fundamentals_source": "SEC_ERROR",
        }
        self.assertEqual(_normalize_data_status(row)["data_status"], "ERROR")

    def test_usable_data_is_ok(self):
        row = {
            "fundamentals_available": True,
            "revenue": 100.0,
            "data_status": "OK",
        }
        self.assertEqual(_normalize_data_status(row)["data_status"], "OK")


if __name__ == "__main__":
    unittest.main()
