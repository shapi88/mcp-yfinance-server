"""
Tests for mcp-yfinance-server tools.

All tests use stub providers — no network calls and no unittest.mock patches needed.
"""

import json
from typing import Any, Dict

import pandas as pd
import pytest

from mcp_yfinance_server.finance.tools.details import get_enhanced_stock_details
from mcp_yfinance_server.finance.tools.drivers import get_top_stock_drivers
from mcp_yfinance_server.finance.tools.history import get_stock_5y_history
from mcp_yfinance_server.finance.tools.metrics import get_advanced_stock_metrics


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


# ---------------------------------------------------------------------------
# Stub providers
# ---------------------------------------------------------------------------

class _StubInfoProvider:
    """Stub for StockInfoProvider."""

    def __init__(self, info: Dict[str, Any] = None, raises: Exception = None):
        self._info = info if info is not None else MOCK_INFO.copy()
        self._raises = raises

    def get_info(self, symbol: str) -> Dict[str, Any]:
        if self._raises:
            raise self._raises
        return self._info


class _StubFinancialsProvider:
    """Stub for StockFinancialsProvider."""

    def __init__(self, empty: bool = False, raises: Exception = None):
        self._empty = empty
        self._raises = raises
        idx = pd.to_datetime(["2023-09-30", "2022-09-30"])
        self._fin_df = pd.DataFrame(
            {"Total Revenue": [400e9, 380e9], "Net Income": [100e9, 95e9]}, index=idx
        )

    def _df(self) -> pd.DataFrame:
        if self._raises:
            raise self._raises
        return pd.DataFrame() if self._empty else self._fin_df

    def get_financials(self, symbol: str) -> pd.DataFrame:
        return self._df()

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._df()

    def get_cashflow(self, symbol: str) -> pd.DataFrame:
        return self._df()

    def get_quarterly_financials(self, symbol: str) -> pd.DataFrame:
        return self._df()

    def get_quarterly_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._df()

    def get_quarterly_cashflow(self, symbol: str) -> pd.DataFrame:
        return self._df()

    def get_analyst_price_targets(self, symbol: str) -> Any:
        return {"mean": 210.0, "high": 250.0, "low": 160.0}

    def get_calendar(self, symbol: str) -> Any:
        return {}


class _StubHistoryProvider:
    """Stub for StockHistoryProvider."""

    def __init__(self, empty: bool = False, history_raises: Exception = None):
        self._empty = empty
        self._history_raises = history_raises
        div_idx = pd.to_datetime(["2023-08-11", "2023-05-12"])
        self._dividends = pd.Series([0.24, 0.24], index=div_idx)
        self._splits = pd.Series(dtype=float)
        self._history_df = pd.DataFrame(
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

    def get_history(self, symbol: str, period: str = "5y", interval: str = "1wk") -> pd.DataFrame:
        if self._history_raises:
            raise self._history_raises
        return pd.DataFrame() if self._empty else self._history_df

    def get_dividends(self, symbol: str) -> pd.Series:
        return pd.Series(dtype=float) if self._empty else self._dividends

    def get_splits(self, symbol: str) -> pd.Series:
        return self._splits


# ---------------------------------------------------------------------------
# Tests: get_advanced_stock_metrics
# ---------------------------------------------------------------------------


class TestGetAdvancedStockMetrics:
    def test_happy_path_single_ticker(self):
        result = json.loads(get_advanced_stock_metrics("AAPL", _StubInfoProvider()))
        assert "AAPL" in result
        data = result["AAPL"]
        assert data["basic_info"]["symbol"] == "AAPL"
        assert data["basic_info"]["sector"] == "Technology"
        assert data["growth_potential"]["revenueGrowth"] == pytest.approx(0.08)
        assert data["valuation_profitability"]["forwardPE"] == pytest.approx(25.0)
        assert data["financial_health_cash"]["freeCashflow"] == 100_000_000_000

    def test_multiple_tickers(self):
        result = json.loads(get_advanced_stock_metrics("AAPL, MSFT", _StubInfoProvider()))
        assert "AAPL" in result
        assert "MSFT" in result

    def test_invalid_ticker_returns_error(self):
        result = json.loads(get_advanced_stock_metrics("INVALID", _StubInfoProvider(info={})))
        assert "error" in result["INVALID"]

    def test_empty_string_returns_error(self):
        result = json.loads(get_advanced_stock_metrics("", _StubInfoProvider()))
        assert "error" in result

    def test_exception_during_fetch_returns_error(self):
        result = json.loads(
            get_advanced_stock_metrics("AAPL", _StubInfoProvider(raises=RuntimeError("Network error")))
        )
        assert "error" in result["AAPL"]


# ---------------------------------------------------------------------------
# Tests: get_enhanced_stock_details
# ---------------------------------------------------------------------------


class TestGetEnhancedStockDetails:
    def _call(self, symbol="AAPL", info=None, empty_frames=False):
        ip = _StubInfoProvider(info=info)
        fp = _StubFinancialsProvider(empty=empty_frames)
        return json.loads(get_enhanced_stock_details(symbol, ip, fp))

    def test_happy_path(self):
        result = self._call()
        assert "AAPL" in result
        data = result["AAPL"]
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
        result = self._call()
        data = result["AAPL"]
        for key in (
            "annual_income_statement", "annual_balance_sheet", "annual_cash_flow",
            "quarterly_income_statement", "quarterly_balance_sheet", "quarterly_cash_flow",
        ):
            assert key in data, f"Missing: {key}"
            assert isinstance(data[key], list)

    def test_empty_frames_graceful(self):
        result = self._call(empty_frames=True)
        data = result["AAPL"]
        assert data["annual_income_statement"] == []

    def test_invalid_symbol_returns_error(self):
        result = self._call(info={})
        assert "error" in result

    def test_exception_returns_error(self):
        ip = _StubInfoProvider(raises=RuntimeError("fail"))
        fp = _StubFinancialsProvider()
        result = json.loads(get_enhanced_stock_details("AAPL", ip, fp))
        assert "error" in result

    def test_symbol_normalised_to_upper(self):
        result = self._call(symbol="aapl")
        assert "AAPL" in result


# ---------------------------------------------------------------------------
# Tests: get_stock_5y_history
# ---------------------------------------------------------------------------


class TestGetStock5yHistory:
    def _call(self, symbol="AAPL", empty=False, history_raises=None):
        hp = _StubHistoryProvider(empty=empty, history_raises=history_raises)
        fp = _StubFinancialsProvider(empty=empty)
        return json.loads(get_stock_5y_history(symbol, hp, fp))

    def test_happy_path(self):
        result = self._call()
        assert result["symbol"] == "AAPL"
        assert "price_history_weekly" in result
        assert len(result["price_history_weekly"]) == 2
        first = result["price_history_weekly"][0]
        assert "open" in first and "high" in first and "close" in first
        assert "volume" in first

    def test_dividends_and_splits(self):
        result = self._call()
        assert isinstance(result["dividends"], list)
        assert len(result["dividends"]) == 2
        assert isinstance(result["stock_splits"], list)

    def test_financial_time_series(self):
        result = self._call()
        for key in (
            "annual_income_statement", "annual_balance_sheet", "annual_cash_flow",
            "quarterly_income_statement", "quarterly_balance_sheet", "quarterly_cash_flow",
        ):
            assert key in result, f"Missing: {key}"

    def test_empty_history_returns_empty_list(self):
        result = self._call(empty=True)
        assert result["price_history_weekly"] == []
        assert result["dividends"] == []

    def test_invalid_symbol_graceful(self):
        result = self._call(history_raises=RuntimeError("bad symbol"))
        assert "price_history_weekly" in result
        assert result["price_history_weekly"] == []

    def test_exception_returns_error(self):
        """A history provider that raises on get_history degrades gracefully to an empty list."""
        hp = _StubHistoryProvider(history_raises=RuntimeError("fail"))
        fp = _StubFinancialsProvider()
        result = json.loads(get_stock_5y_history("AAPL", hp, fp))
        assert result["price_history_weekly"] == []

    def test_symbol_normalised_to_upper(self):
        result = self._call(symbol="aapl")
        assert result["symbol"] == "AAPL"


# ---------------------------------------------------------------------------
# Tests: get_top_stock_drivers
# ---------------------------------------------------------------------------


class TestGetTopStockDrivers:
    def _call(self, info: Dict[str, Any] = None) -> Dict[str, Any]:
        return json.loads(get_top_stock_drivers("AAPL", _StubInfoProvider(info=info)))

    def test_happy_path_structure(self):
        result = self._call()
        assert result["symbol"] == "AAPL"
        assert "overall_score" in result
        assert "signal" in result
        assert "drivers" in result
        assert len(result["drivers"]) == 10

    def test_all_driver_fields_present(self):
        result = self._call()
        for d in result["drivers"]:
            assert "driver" in d
            assert "score" in d
            assert "weight" in d
            assert "weighted_score" in d
            assert "metrics" in d
            assert "explanation" in d

    def test_score_range(self):
        result = self._call()
        for d in result["drivers"]:
            assert 0 <= d["score"] <= 4

    def test_overall_score_range(self):
        result = self._call()
        assert 0.0 <= result["overall_score"] <= 4.0

    def test_signal_valid_values(self):
        result = self._call()
        assert result["signal"] in {"Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"}

    def test_weighted_scores_non_negative(self):
        result = self._call()
        for d in result["drivers"]:
            assert d["weighted_score"] >= 0

    def test_invalid_symbol_returns_error(self):
        result = json.loads(get_top_stock_drivers("ZZZZ", _StubInfoProvider(info={})))
        assert "error" in result

    def test_exception_returns_error(self):
        result = json.loads(
            get_top_stock_drivers("AAPL", _StubInfoProvider(raises=RuntimeError("fail")))
        )
        assert "error" in result

    def test_missing_metrics_handled_gracefully(self):
        sparse_info = {"symbol": "SPARSE", "currentPrice": 50.0}
        result = self._call(info=sparse_info)
        assert len(result["drivers"]) == 10
        for d in result["drivers"]:
            assert 0 <= d["score"] <= 4

    def test_symbol_normalised_to_upper(self):
        result = json.loads(get_top_stock_drivers("aapl", _StubInfoProvider()))
        assert result["symbol"] == "AAPL"

    def test_strong_buy_signal_for_excellent_stock(self):
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
        result = self._call(info=excellent)
        assert result["signal"] in {"Strong Buy", "Buy"}
