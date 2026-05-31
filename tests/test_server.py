"""
Tests for mcp-yfinance-server tools.

All external network calls are mocked so tests run offline.
"""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import server


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_INFO: Dict[str, Any] = {
    "symbol": "AAPL",
    "longName": "Apple Inc.",
    "shortName": "Apple",
    "exchange": "NMS",
    "quoteType": "EQUITY",
    "currency": "USD",
    "financialCurrency": "USD",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "fullTimeEmployees": 160000,
    "website": "https://www.apple.com",
    "city": "Cupertino",
    "state": "CA",
    "country": "United States",
    "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones.",
    "currentPrice": 190.0,
    "previousClose": 188.5,
    "open": 189.0,
    "dayLow": 187.5,
    "dayHigh": 192.0,
    "regularMarketPreviousClose": 188.5,
    "regularMarketOpen": 189.0,
    "regularMarketDayLow": 187.5,
    "regularMarketDayHigh": 192.0,
    "regularMarketVolume": 60_000_000,
    "volume": 60_000_000,
    "averageVolume": 55_000_000,
    "averageVolume10days": 57_000_000,
    "marketCap": 3_000_000_000_000,
    "fiftyTwoWeekLow": 130.0,
    "fiftyTwoWeekHigh": 200.0,
    "fiftyTwoWeekChange": 0.25,
    "SandP52WeekChange": 0.18,
    "fiftyDayAverage": 185.0,
    "twoHundredDayAverage": 175.0,
    "bid": 189.9,
    "ask": 190.1,
    "bidSize": 100,
    "askSize": 200,
    "priceToSalesTrailing12Months": 7.5,
    "trailingPE": 28.0,
    "forwardPE": 25.0,
    "trailingEps": 6.5,
    "forwardEps": 7.3,
    "priceToBook": 40.0,
    "bookValue": 4.5,
    "enterpriseValue": 2_900_000_000_000,
    "enterpriseToRevenue": 7.2,
    "enterpriseToEbitda": 22.0,
    "pegRatio": 2.1,
    "dividendRate": 0.96,
    "dividendYield": 0.005,
    "exDividendDate": 1700000000,
    "payoutRatio": 0.16,
    "fiveYearAvgDividendYield": 0.007,
    "trailingAnnualDividendRate": 0.96,
    "trailingAnnualDividendYield": 0.005,
    "lastDividendValue": 0.24,
    "lastDividendDate": 1700000000,
    "totalRevenue": 400_000_000_000,
    "revenuePerShare": 25.0,
    "revenueGrowth": 0.08,
    "grossMargins": 0.44,
    "operatingMargins": 0.30,
    "profitMargins": 0.25,
    "ebitdaMargins": 0.32,
    "netIncomeToCommon": 100_000_000_000,
    "earningsGrowth": 0.12,
    "earningsQuarterlyGrowth": 0.10,
    "returnOnAssets": 0.20,
    "returnOnEquity": 1.50,
    "totalCash": 60_000_000_000,
    "totalCashPerShare": 3.8,
    "totalDebt": 110_000_000_000,
    "debtToEquity": 150.0,
    "currentRatio": 1.0,
    "quickRatio": 0.9,
    "operatingCashflow": 115_000_000_000,
    "freeCashflow": 100_000_000_000,
    "grossProfits": 175_000_000_000,
    "ebitda": 130_000_000_000,
    "sharesOutstanding": 15_800_000_000,
    "floatShares": 15_700_000_000,
    "sharesShort": 100_000_000,
    "sharesShortPriorMonth": 90_000_000,
    "shortRatio": 1.5,
    "shortPercentOfFloat": 0.006,
    "heldPercentInsiders": 0.03,
    "heldPercentInstitutions": 0.60,
    "impliedSharesOutstanding": 15_800_000_000,
    "recommendationMean": 1.8,
    "recommendationKey": "buy",
    "numberOfAnalystOpinions": 40,
    "targetHighPrice": 250.0,
    "targetLowPrice": 160.0,
    "targetMeanPrice": 210.0,
    "targetMedianPrice": 210.0,
    "auditRisk": 3,
    "boardRisk": 2,
    "compensationRisk": 4,
    "shareHolderRightsRisk": 2,
    "overallRisk": 3,
    "mostRecentQuarter": 1700000000,
    "lastFiscalYearEnd": 1694000000,
    "nextFiscalYearEnd": 1725000000,
    "earningsTimestamp": 1710000000,
    "earningsTimestampStart": 1709000000,
    "earningsTimestampEnd": 1711000000,
}


def _make_mock_ticker(info: Dict[str, Any] = None, empty_frames: bool = False) -> MagicMock:
    """Build a MagicMock that mimics yf.Ticker for the given info dict."""
    mock = MagicMock()
    mock.info = info if info is not None else MOCK_INFO.copy()

    empty_df = pd.DataFrame()
    empty_series = pd.Series(dtype=float)

    if empty_frames:
        mock.financials = empty_df
        mock.balance_sheet = empty_df
        mock.cashflow = empty_df
        mock.quarterly_financials = empty_df
        mock.quarterly_balance_sheet = empty_df
        mock.quarterly_cashflow = empty_df
        mock.dividends = empty_series
        mock.splits = empty_series
        mock.history.return_value = empty_df
        mock.analyst_price_targets = {}
        mock.calendar = {}
    else:
        # Minimal financial DataFrames
        idx = pd.to_datetime(["2023-09-30", "2022-09-30"])
        fin_df = pd.DataFrame(
            {"Total Revenue": [400e9, 380e9], "Net Income": [100e9, 95e9]}, index=idx
        )
        mock.financials = fin_df
        mock.quarterly_financials = fin_df
        mock.balance_sheet = fin_df
        mock.quarterly_balance_sheet = fin_df
        mock.cashflow = fin_df
        mock.quarterly_cashflow = fin_df

        div_idx = pd.to_datetime(["2023-08-11", "2023-05-12"])
        mock.dividends = pd.Series([0.24, 0.24], index=div_idx)
        mock.splits = pd.Series(dtype=float)
        mock.history.return_value = pd.DataFrame(
            {
                "Open": [180.0, 182.0],
                "High": [192.0, 193.0],
                "Low": [178.0, 180.0],
                "Close": [190.0, 191.0],
                "Volume": [60_000_000, 55_000_000],
                "Dividends": [0.0, 0.24],
                "Stock Splits": [0.0, 0.0],
            },
            index=pd.to_datetime(["2024-01-05", "2024-01-12"]),
        )
        mock.analyst_price_targets = {"mean": 210.0, "high": 250.0, "low": 160.0}
        mock.calendar = {}

    return mock


# ---------------------------------------------------------------------------
# Tests: get_advanced_stock_metrics (existing tool – backward compat)
# ---------------------------------------------------------------------------


class TestGetAdvancedStockMetrics:
    def test_happy_path_single_ticker(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_advanced_stock_metrics("AAPL"))
        assert "AAPL" in result
        data = result["AAPL"]
        assert data["basic_info"]["symbol"] == "AAPL"
        assert data["basic_info"]["sector"] == "Technology"
        assert data["growth_potential"]["revenueGrowth"] == pytest.approx(0.08)
        assert data["valuation_profitability"]["forwardPE"] == pytest.approx(25.0)
        assert data["financial_health_cash"]["freeCashflow"] == 100_000_000_000

    def test_multiple_tickers(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_advanced_stock_metrics("AAPL, MSFT"))
        assert "AAPL" in result
        assert "MSFT" in result

    def test_invalid_ticker_returns_error(self):
        mock = _make_mock_ticker(info={})
        with patch("server.yf.Ticker", return_value=mock):
            result = json.loads(server.get_advanced_stock_metrics("INVALID"))
        assert "error" in result["INVALID"]

    def test_empty_string_returns_error(self):
        result = json.loads(server.get_advanced_stock_metrics(""))
        assert "error" in result

    def test_exception_during_fetch_returns_error(self):
        with patch("server.yf.Ticker", side_effect=RuntimeError("Network error")):
            result = json.loads(server.get_advanced_stock_metrics("AAPL"))
        # The per-ticker except catches it
        assert "error" in result["AAPL"]


# ---------------------------------------------------------------------------
# Tests: get_enhanced_stock_details
# ---------------------------------------------------------------------------


class TestGetEnhancedStockDetails:
    def test_happy_path(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_enhanced_stock_details("AAPL"))
        assert "AAPL" in result
        data = result["AAPL"]
        # All expected categories present
        for cat in (
            "identity", "price_market", "valuation", "dividends",
            "financials", "shares_ownership", "analyst_targets",
            "governance_risk", "earnings_dates",
        ):
            assert cat in data, f"Missing category: {cat}"
        assert data["identity"]["symbol"] == "AAPL"
        assert data["valuation"]["trailingPE"] == pytest.approx(28.0)
        assert data["financials"]["operatingMargins"] == pytest.approx(0.30)

    def test_financial_statements_present(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_enhanced_stock_details("AAPL"))
        data = result["AAPL"]
        for key in (
            "annual_income_statement", "annual_balance_sheet", "annual_cash_flow",
            "quarterly_income_statement", "quarterly_balance_sheet", "quarterly_cash_flow",
        ):
            assert key in data, f"Missing: {key}"
            assert isinstance(data[key], list)

    def test_empty_frames_graceful(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker(empty_frames=True)):
            result = json.loads(server.get_enhanced_stock_details("AAPL"))
        data = result["AAPL"]
        assert data["annual_income_statement"] == []

    def test_invalid_symbol_returns_error(self):
        mock = _make_mock_ticker(info={})
        with patch("server.yf.Ticker", return_value=mock):
            result = json.loads(server.get_enhanced_stock_details("ZZZZ"))
        assert "error" in result

    def test_exception_returns_error(self):
        with patch("server.yf.Ticker", side_effect=RuntimeError("fail")):
            result = json.loads(server.get_enhanced_stock_details("AAPL"))
        assert "error" in result

    def test_symbol_normalised_to_upper(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_enhanced_stock_details("aapl"))
        assert "AAPL" in result


# ---------------------------------------------------------------------------
# Tests: get_stock_5y_history
# ---------------------------------------------------------------------------


class TestGetStock5yHistory:
    def test_happy_path(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_stock_5y_history("AAPL"))
        assert result["symbol"] == "AAPL"
        assert "price_history_weekly" in result
        assert len(result["price_history_weekly"]) == 2
        first = result["price_history_weekly"][0]
        assert "open" in first and "high" in first and "close" in first
        assert "volume" in first

    def test_dividends_and_splits(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_stock_5y_history("AAPL"))
        assert isinstance(result["dividends"], list)
        assert len(result["dividends"]) == 2
        assert isinstance(result["stock_splits"], list)

    def test_financial_time_series(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_stock_5y_history("AAPL"))
        for key in (
            "annual_income_statement", "annual_balance_sheet", "annual_cash_flow",
            "quarterly_income_statement", "quarterly_balance_sheet", "quarterly_cash_flow",
        ):
            assert key in result, f"Missing: {key}"

    def test_empty_history_returns_empty_list(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker(empty_frames=True)):
            result = json.loads(server.get_stock_5y_history("AAPL"))
        assert result["price_history_weekly"] == []
        assert result["dividends"] == []

    def test_invalid_symbol_graceful(self):
        """An invalid symbol whose history() raises should return empty price_history_weekly."""
        mock = _make_mock_ticker(info={"symbol": "ZZZZ"})
        mock.history.side_effect = RuntimeError("bad symbol")
        with patch("server.yf.Ticker", return_value=mock):
            result = json.loads(server.get_stock_5y_history("ZZZZ"))
        assert "price_history_weekly" in result
        assert result["price_history_weekly"] == []

    def test_exception_returns_error(self):
        with patch("server.yf.Ticker", side_effect=RuntimeError("fail")):
            result = json.loads(server.get_stock_5y_history("AAPL"))
        assert "error" in result

    def test_symbol_normalised_to_upper(self):
        with patch("server.yf.Ticker", return_value=_make_mock_ticker()):
            result = json.loads(server.get_stock_5y_history("aapl"))
        assert result["symbol"] == "AAPL"


# ---------------------------------------------------------------------------
# Tests: get_top_stock_drivers
# ---------------------------------------------------------------------------


class TestGetTopStockDrivers:
    def _get_drivers(self, info: Dict[str, Any] = None) -> Dict[str, Any]:
        mock = _make_mock_ticker(info=info)
        with patch("server.yf.Ticker", return_value=mock):
            return json.loads(server.get_top_stock_drivers("AAPL"))

    def test_happy_path_structure(self):
        result = self._get_drivers()
        assert result["symbol"] == "AAPL"
        assert "overall_score" in result
        assert "signal" in result
        assert "drivers" in result
        assert len(result["drivers"]) == 10

    def test_all_driver_fields_present(self):
        result = self._get_drivers()
        for d in result["drivers"]:
            assert "driver" in d
            assert "score" in d
            assert "weight" in d
            assert "weighted_score" in d
            assert "metrics" in d
            assert "explanation" in d

    def test_score_range(self):
        result = self._get_drivers()
        for d in result["drivers"]:
            assert 0 <= d["score"] <= 4

    def test_overall_score_range(self):
        result = self._get_drivers()
        assert 0.0 <= result["overall_score"] <= 4.0

    def test_signal_valid_values(self):
        result = self._get_drivers()
        assert result["signal"] in {"Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"}

    def test_weighted_scores_non_negative(self):
        result = self._get_drivers()
        for d in result["drivers"]:
            assert d["weighted_score"] >= 0

    def test_invalid_symbol_returns_error(self):
        mock = _make_mock_ticker(info={})
        with patch("server.yf.Ticker", return_value=mock):
            result = json.loads(server.get_top_stock_drivers("ZZZZ"))
        assert "error" in result

    def test_exception_returns_error(self):
        with patch("server.yf.Ticker", side_effect=RuntimeError("fail")):
            result = json.loads(server.get_top_stock_drivers("AAPL"))
        assert "error" in result

    def test_missing_metrics_handled_gracefully(self):
        """Driver tool should work even if most metrics are absent."""
        sparse_info = {"symbol": "SPARSE", "currentPrice": 50.0}
        result = self._get_drivers(info=sparse_info)
        assert len(result["drivers"]) == 10
        for d in result["drivers"]:
            assert 0 <= d["score"] <= 4

    def test_symbol_normalised_to_upper(self):
        mock = _make_mock_ticker()
        with patch("server.yf.Ticker", return_value=mock):
            result = json.loads(server.get_top_stock_drivers("aapl"))
        assert result["symbol"] == "AAPL"

    def test_strong_buy_signal_for_excellent_stock(self):
        """A stock with very attractive metrics should score ≥ 2.4 (Buy or better)."""
        excellent = MOCK_INFO.copy()
        excellent.update({
            "forwardPE": 8.0, "priceToBook": 1.0, "enterpriseToEbitda": 5.0,
            "revenueGrowth": 0.30, "earningsGrowth": 0.30, "pegRatio": 0.8,
            "operatingMargins": 0.35, "profitMargins": 0.30, "returnOnEquity": 0.35,
            "debtToEquity": 20.0, "currentRatio": 3.0,
            "freeCashflow": 50e9, "marketCap": 500e9,
            "fiftyTwoWeekLow": 80.0, "fiftyTwoWeekHigh": 200.0, "currentPrice": 195.0,
            "fiftyDayAverage": 180.0, "twoHundredDayAverage": 160.0,
            "recommendationMean": 1.2, "targetMeanPrice": 260.0,
            "dividendYield": 0.04, "payoutRatio": 0.40,
            "trailingEps": 5.0, "forwardEps": 8.0,
            "shortPercentOfFloat": 0.01,
            "heldPercentInstitutions": 0.80, "heldPercentInsiders": 0.15,
        })
        result = self._get_drivers(info=excellent)
        assert result["signal"] in {"Strong Buy", "Buy"}


# ---------------------------------------------------------------------------
# Tests: internal helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_safe_float_normal(self):
        assert server._safe_float(3.14) == pytest.approx(3.14)

    def test_safe_float_nan_returns_none(self):
        assert server._safe_float(float("nan")) is None

    def test_safe_float_inf_returns_none(self):
        assert server._safe_float(float("inf")) is None

    def test_safe_float_none_returns_none(self):
        assert server._safe_float(None) is None

    def test_safe_float_string_number(self):
        assert server._safe_float("42.5") == pytest.approx(42.5)

    def test_safe_int_normal(self):
        assert server._safe_int(7) == 7

    def test_safe_int_none_returns_none(self):
        assert server._safe_int(None) is None

    def test_series_to_records_empty(self):
        assert server._series_to_records(pd.Series(dtype=float)) == []

    def test_series_to_records_values(self):
        s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
        records = server._series_to_records(s)
        assert len(records) == 2
        assert records[0]["date"] == "2024-01-01"
        assert records[0]["value"] == pytest.approx(1.0)

    def test_df_to_records_empty(self):
        assert server._df_to_records(pd.DataFrame()) == []

    def test_df_to_records_values(self):
        df = pd.DataFrame(
            {"Revenue": [100.0, 200.0]},
            index=pd.to_datetime(["2023-01-01", "2022-01-01"]),
        )
        records = server._df_to_records(df)
        assert len(records) == 2
        assert records[0]["date"] == "2023-01-01"
        assert records[0]["Revenue"] == pytest.approx(100.0)

    def test_score_metric_higher_better(self):
        assert server._score_metric(30, "higher_better", [5, 10, 20, 25]) == 4
        assert server._score_metric(12, "higher_better", [5, 10, 20, 25]) == 2
        assert server._score_metric(1, "higher_better", [5, 10, 20, 25]) == 0

    def test_score_metric_lower_better(self):
        assert server._score_metric(1, "lower_better", [5, 10, 20, 25]) == 4
        assert server._score_metric(15, "lower_better", [5, 10, 20, 25]) == 2
        assert server._score_metric(30, "lower_better", [5, 10, 20, 25]) == 0

    def test_score_metric_none_returns_zero(self):
        assert server._score_metric(None, "higher_better", [1, 2, 3, 4]) == 0
