import unittest

from scanner import _normalize_data_status


class DataQualityStatusTests(unittest.TestCase):
    def test_unusable_sec_cache_cannot_remain_ok(self):
        row = {
            "fundamentals_available": False,
            "data_quality": "D",
            "data_status": "OK",
            "fundamentals_source": "SEC_CACHE",
        }
        self.assertEqual(_normalize_data_status(row)["data_status"], "INCOMPLETE")

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
