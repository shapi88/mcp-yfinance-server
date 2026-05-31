"""
Unit tests for finance.transformers.
"""
import pandas as pd
import pytest

from mcp_yfinance_server.finance.transformers import df_to_records, safe_float, safe_int, series_to_records


class TestSafeFloat:
    def test_normal(self):
        assert safe_float(3.14) == pytest.approx(3.14)

    def test_nan_returns_none(self):
        assert safe_float(float("nan")) is None

    def test_inf_returns_none(self):
        assert safe_float(float("inf")) is None

    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_string_number(self):
        assert safe_float("42.5") == pytest.approx(42.5)

    def test_invalid_string_returns_none(self):
        assert safe_float("abc") is None


class TestSafeInt:
    def test_normal(self):
        assert safe_int(7) == 7

    def test_none_returns_none(self):
        assert safe_int(None) is None

    def test_string_number(self):
        assert safe_int("5") == 5

    def test_invalid_string_returns_none(self):
        assert safe_int("abc") is None


class TestSeriesToRecords:
    def test_empty_returns_empty_list(self):
        assert series_to_records(pd.Series(dtype=float)) == []

    def test_none_returns_empty_list(self):
        assert series_to_records(None) == []

    def test_values(self):
        s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
        records = series_to_records(s)
        assert len(records) == 2
        assert records[0]["date"] == "2024-01-01"
        assert records[0]["value"] == pytest.approx(1.0)

    def test_nan_value_becomes_none(self):
        import math
        s = pd.Series([float("nan")], index=pd.to_datetime(["2024-01-01"]))
        records = series_to_records(s)
        assert records[0]["value"] is None


class TestDfToRecords:
    def test_empty_returns_empty_list(self):
        assert df_to_records(pd.DataFrame()) == []

    def test_none_returns_empty_list(self):
        assert df_to_records(None) == []

    def test_values(self):
        df = pd.DataFrame(
            {"Revenue": [100.0, 200.0]},
            index=pd.to_datetime(["2023-01-01", "2022-01-01"]),
        )
        records = df_to_records(df)
        assert len(records) == 2
        assert records[0]["date"] == "2023-01-01"
        assert records[0]["Revenue"] == pytest.approx(100.0)

    def test_int_column_preserved(self):
        df = pd.DataFrame(
            {"Count": [10, 20]},
            index=pd.to_datetime(["2023-01-01", "2022-01-01"]),
        )
        records = df_to_records(df)
        assert records[0]["Count"] == 10
