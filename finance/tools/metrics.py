"""
Tool: get_advanced_stock_metrics

Fetches comprehensive stock metrics for one or more ticker symbols.
"""
import json
import logging
from typing import Any, Dict

from finance.providers import StockInfoProvider

logger = logging.getLogger("mcp-yfinance-server")


def get_advanced_stock_metrics(tickers: str, provider: StockInfoProvider) -> str:
    """
    Fetch comprehensive stock data and key metrics for one or more ticker symbols.

    This tool retrieves basic info, growth potential, valuation, profitability,
    and financial health metrics from Yahoo Finance to help evaluate the stock's
    future potential.

    Args:
        tickers:  A comma-separated list of stock ticker symbols
                  (e.g., 'AAPL' or 'AAPL, MSFT, TSLA').
        provider: A StockInfoProvider used to retrieve data.

    Returns:
        A JSON string mapping each ticker symbol to its retrieved metrics or
        error message.
    """
    logger.info(f"Fetching advanced metrics for tickers: {tickers}")
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

        if not ticker_list:
            return json.dumps(
                {"error": "Ticker list cannot be empty. Please provide at least one valid ticker symbol."},
                indent=2,
            )

        results: Dict[str, Any] = {}

        for ticker in ticker_list:
            try:
                info = provider.get_info(ticker)

                if not info or not isinstance(info, dict) or not info.get("symbol"):
                    results[ticker] = {
                        "error": f"No data found for ticker '{ticker}'. Please verify the symbol is correct."
                    }
                    continue

                results[ticker] = {
                    "basic_info": {
                        "symbol": info.get("symbol"),
                        "longName": info.get("longName"),
                        "currentPrice": info.get("currentPrice"),
                        "marketCap": info.get("marketCap"),
                        "sector": info.get("sector"),
                        "industry": info.get("industry"),
                    },
                    "growth_potential": {
                        "pegRatio": info.get("pegRatio"),
                        "earningsGrowth": info.get("earningsGrowth"),
                        "revenueGrowth": info.get("revenueGrowth"),
                    },
                    "valuation_profitability": {
                        "forwardPE": info.get("forwardPE"),
                        "trailingPE": info.get("trailingPE"),
                        "priceToBook": info.get("priceToBook"),
                        "returnOnEquity": info.get("returnOnEquity"),
                        "operatingMargins": info.get("operatingMargins"),
                    },
                    "financial_health_cash": {
                        "totalDebt": info.get("totalDebt"),
                        "freeCashflow": info.get("freeCashflow"),
                        "debtToEquity": info.get("debtToEquity"),
                    },
                }
            except Exception as e:
                logger.error(f"Error fetching data for ticker {ticker}: {e}")
                results[ticker] = {"error": f"An error occurred while fetching metrics: {e}"}

        return json.dumps(results, indent=2)

    except Exception as e:
        logger.error(f"Error processing tickers string '{tickers}': {e}")
        return json.dumps({"error": f"An error occurred while processing tickers: {e}"}, indent=2)
