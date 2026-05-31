"""
MCP server entry point.

This module only handles:
  - Logging setup
  - FastMCP initialisation
  - MCP tool registration (delegating all logic to finance/tools/)
"""
import logging

from mcp.server.fastmcp import FastMCP

from finance.providers import YFinanceProvider
from finance.tools.details import get_enhanced_stock_details as _get_enhanced_stock_details
from finance.tools.drivers import get_top_stock_drivers as _get_top_stock_drivers
from finance.tools.history import get_stock_5y_history as _get_stock_5y_history
from finance.tools.metrics import get_advanced_stock_metrics as _get_advanced_stock_metrics

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-yfinance-server")

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("Advanced-Finance-Server")

_provider = YFinanceProvider()

# ---------------------------------------------------------------------------
# Tool registrations
# ---------------------------------------------------------------------------


@mcp.tool()
def get_advanced_stock_metrics(tickers: str) -> str:
    """
    Fetch comprehensive stock data and key metrics for one or more ticker symbols.

    This tool retrieves basic info, growth potential, valuation, profitability,
    and financial health metrics from Yahoo Finance to help evaluate the stock's
    future potential.

    Args:
        tickers: A comma-separated list of stock ticker symbols
                 (e.g., 'AAPL' or 'AAPL, MSFT, TSLA').

    Returns:
        A JSON string mapping each ticker symbol to its retrieved metrics or
        error message.
    """
    return _get_advanced_stock_metrics(tickers, _provider)


@mcp.tool()
def get_enhanced_stock_details(symbol: str) -> str:
    """
    Return a comprehensive, normalised stock profile for a single ticker.

    Aggregates all non-deprecated yfinance data sources:
      - Categorised info fields (identity, price/market, valuation, dividends,
        financials, shares/ownership, analyst targets, governance risk,
        earnings dates)
      - Latest annual income statement, balance sheet, and cash-flow statement
      - Latest quarterly income statement, balance sheet, and cash-flow statement
      - Analyst price targets and recommendation summary
      - Upcoming earnings calendar

    Args:
        symbol: A single stock ticker symbol (e.g. 'AAPL').

    Returns:
        A JSON string with the full stock profile grouped by category,
        or an error message if the symbol is invalid or data is unavailable.
    """
    return _get_enhanced_stock_details(symbol, _provider, _provider)


@mcp.tool()
def get_stock_5y_history(symbol: str) -> str:
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
        symbol: A single stock ticker symbol (e.g. 'AAPL').

    Returns:
        A JSON string with keys for each historical dimension, or an error message.
    """
    return _get_stock_5y_history(symbol, _provider, _provider)


@mcp.tool()
def get_top_stock_drivers(symbol: str) -> str:
    """
    Identify and score the top 10 main drivers of a stock's investment case.

    Each driver is evaluated using key yfinance metrics. Scores range from
    0 (weakest) to 4 (strongest) based on industry-standard thresholds.
    The 10 drivers analysed are:

      1.  Valuation          – Forward P/E, P/B, EV/EBITDA
      2.  Growth             – Revenue growth, earnings growth, PEG ratio
      3.  Profitability      – Operating margins, net margins, ROE
      4.  Financial Health   – Debt/equity, current ratio, free cash flow yield
      5.  Price Momentum     – Position vs 52-week range, vs 50-/200-day MA
      6.  Analyst Sentiment  – Recommendation mean, target price upside
      7.  Dividend Quality   – Dividend yield, payout ratio sustainability
      8.  Earnings Quality   – EPS growth, quarterly earnings growth, earnings trend
      9.  Short Interest     – Short % of float (lower = less headwind)
      10. Institutional Support – % held by institutions, insider alignment

    Args:
        symbol: A single stock ticker symbol (e.g. 'AAPL').

    Returns:
        A JSON string with a ranked list of the 10 drivers, each containing:
          - driver (name)
          - score (0-4)
          - weight (relative importance, sums to 1.0)
          - weighted_score
          - metrics (raw values used)
          - explanation (plain-English rationale)
        Plus an overall_score (0-4) and signal (Strong Buy / Buy / Hold / Sell / Strong Sell).
    """
    return _get_top_stock_drivers(symbol, _provider)


if __name__ == "__main__":
    mcp.run()
