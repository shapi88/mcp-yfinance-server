"""
Provider protocols and concrete implementations.

Segregated interfaces (ISP) allow each tool to depend only on the capabilities it needs.
The concrete YFinanceProvider satisfies all protocols, enabling substitution (LSP).
"""
from typing import Any, Dict, Optional, runtime_checkable

import pandas as pd
import yfinance as yf
from typing import Protocol


@runtime_checkable
class StockInfoProvider(Protocol):
    """Provides summary info for a stock symbol."""

    def get_info(self, symbol: str) -> Dict[str, Any]:
        """Return the info dict for *symbol* (empty dict if unavailable)."""
        ...


@runtime_checkable
class StockHistoryProvider(Protocol):
    """Provides historical price/corporate-action data."""

    def get_history(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        """Return OHLCV DataFrame for *symbol* over *period* at *interval*."""
        ...

    def get_dividends(self, symbol: str) -> pd.Series:
        """Return dividend Series for *symbol*."""
        ...

    def get_splits(self, symbol: str) -> pd.Series:
        """Return stock-split Series for *symbol*."""
        ...


@runtime_checkable
class StockFinancialsProvider(Protocol):
    """Provides financial statement data."""

    def get_financials(self, symbol: str) -> pd.DataFrame:
        """Return annual income statement DataFrame for *symbol*."""
        ...

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Return annual balance sheet DataFrame for *symbol*."""
        ...

    def get_cashflow(self, symbol: str) -> pd.DataFrame:
        """Return annual cash-flow DataFrame for *symbol*."""
        ...

    def get_quarterly_financials(self, symbol: str) -> pd.DataFrame:
        """Return quarterly income statement DataFrame for *symbol*."""
        ...

    def get_quarterly_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Return quarterly balance sheet DataFrame for *symbol*."""
        ...

    def get_quarterly_cashflow(self, symbol: str) -> pd.DataFrame:
        """Return quarterly cash-flow DataFrame for *symbol*."""
        ...

    def get_analyst_price_targets(self, symbol: str) -> Any:
        """Return analyst price targets (dict or DataFrame) for *symbol*."""
        ...

    def get_calendar(self, symbol: str) -> Any:
        """Return earnings calendar (dict or DataFrame) for *symbol*."""
        ...


class YFinanceProvider:
    """Concrete provider backed by yfinance. Satisfies all three protocols."""

    # Cache Ticker objects within a single provider instance to avoid repeated
    # construction when multiple methods are called for the same symbol.
    def _ticker(self, symbol: str) -> yf.Ticker:
        return yf.Ticker(symbol)

    # --- StockInfoProvider ---

    def get_info(self, symbol: str) -> Dict[str, Any]:
        return self._ticker(symbol).info or {}

    # --- StockHistoryProvider ---

    def get_history(self, symbol: str, period: str = "5y", interval: str = "1wk") -> pd.DataFrame:
        return self._ticker(symbol).history(period=period, interval=interval)

    def get_dividends(self, symbol: str) -> pd.Series:
        return self._ticker(symbol).dividends

    def get_splits(self, symbol: str) -> pd.Series:
        return self._ticker(symbol).splits

    # --- StockFinancialsProvider ---

    def get_financials(self, symbol: str) -> pd.DataFrame:
        return self._ticker(symbol).financials

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._ticker(symbol).balance_sheet

    def get_cashflow(self, symbol: str) -> pd.DataFrame:
        return self._ticker(symbol).cashflow

    def get_quarterly_financials(self, symbol: str) -> pd.DataFrame:
        return self._ticker(symbol).quarterly_financials

    def get_quarterly_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._ticker(symbol).quarterly_balance_sheet

    def get_quarterly_cashflow(self, symbol: str) -> pd.DataFrame:
        return self._ticker(symbol).quarterly_cashflow

    def get_analyst_price_targets(self, symbol: str) -> Any:
        return self._ticker(symbol).analyst_price_targets

    def get_calendar(self, symbol: str) -> Any:
        return self._ticker(symbol).calendar
