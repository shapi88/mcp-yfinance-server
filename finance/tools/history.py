"""
Tool: get_stock_5y_history

Returns 5-year historical data for a single stock across all available dimensions.
"""
import json
import logging
from typing import Any, Dict

from finance.providers import StockFinancialsProvider, StockHistoryProvider, StockInfoProvider
from finance.transformers import df_to_records, safe_float, safe_int, series_to_records

logger = logging.getLogger("mcp-yfinance-server")


def get_stock_5y_history(
    symbol: str,
    history_provider: StockHistoryProvider,
    financials_provider: StockFinancialsProvider,
) -> str:
    """
    Return 5-year historical data for a single stock across all available dimensions.

    Dimensions included (where available for the symbol):
      - Weekly OHLCV price/volume data (5 years)
      - Corporate actions: dividends and stock splits
      - Annual income statement, balance sheet, and cash-flow time series
      - Quarterly income statement, balance sheet, and cash-flow time series

    Each dimension degrades gracefully: if a data source is unavailable for the
    given symbol, that key is returned as an empty list rather than raising an error.

    Args:
        symbol:              A single stock ticker symbol (e.g. 'AAPL').
        history_provider:    Provides historical price and corporate-action data.
        financials_provider: Provides financial statement data.

    Returns:
        A JSON string with keys for each historical dimension, or an error message.
    """
    logger.info(f"Fetching 5-year history for: {symbol}")
    sym = symbol.strip().upper()
    try:
        result: Dict[str, Any] = {"symbol": sym}

        # --- Price / volume (weekly, 5 years) ---
        try:
            hist = history_provider.get_history(sym, period="5y", interval="1wk")
            if hist is not None and not hist.empty:
                price_records = []
                for idx, row in hist.iterrows():
                    price_records.append({
                        "date": str(idx)[:10],
                        "open": safe_float(row.get("Open")),
                        "high": safe_float(row.get("High")),
                        "low": safe_float(row.get("Low")),
                        "close": safe_float(row.get("Close")),
                        "volume": safe_int(row.get("Volume")),
                        "dividends": safe_float(row.get("Dividends", 0)),
                        "stock_splits": safe_float(row.get("Stock Splits", 0)),
                    })
                result["price_history_weekly"] = price_records
            else:
                result["price_history_weekly"] = []
        except Exception as e:
            logger.warning(f"price_history unavailable for {sym}: {e}")
            result["price_history_weekly"] = []

        # --- Dividends ---
        try:
            result["dividends"] = series_to_records(history_provider.get_dividends(sym))
        except Exception:
            result["dividends"] = []

        # --- Stock splits ---
        try:
            result["stock_splits"] = series_to_records(history_provider.get_splits(sym))
        except Exception:
            result["stock_splits"] = []

        # --- Financial statements helper ---
        def _stmt(getter_name: str, label: str) -> None:
            try:
                df = getattr(financials_provider, getter_name)(sym)
                result[label] = df_to_records(df.T) if (df is not None and not df.empty) else []
            except Exception as e:
                logger.warning(f"{label} unavailable for {sym}: {e}")
                result[label] = []

        _stmt("get_financials",             "annual_income_statement")
        _stmt("get_balance_sheet",          "annual_balance_sheet")
        _stmt("get_cashflow",               "annual_cash_flow")
        _stmt("get_quarterly_financials",   "quarterly_income_statement")
        _stmt("get_quarterly_balance_sheet","quarterly_balance_sheet")
        _stmt("get_quarterly_cashflow",     "quarterly_cash_flow")

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"Error fetching 5y history for {sym}: {e}")
        return json.dumps(
            {"error": f"Failed to fetch 5-year history for '{sym}': {e}"}, indent=2
        )
