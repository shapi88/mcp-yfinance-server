"""
Tool: get_enhanced_stock_details

Returns a comprehensive, normalised stock profile for a single ticker.
"""
import json
import logging
from typing import Any, Dict, List

from finance.providers import StockFinancialsProvider, StockInfoProvider
from finance.transformers import df_to_records

logger = logging.getLogger("mcp-yfinance-server")

# ---------------------------------------------------------------------------
# Categorised field map — data-only constant, no logic co-mingled (OCP)
# ---------------------------------------------------------------------------
INFO_FIELD_MAP: Dict[str, List[str]] = {
    "identity": [
        "symbol", "longName", "shortName", "exchange", "quoteType",
        "currency", "financialCurrency", "sector", "industry",
        "fullTimeEmployees", "website", "city", "state", "country",
        "longBusinessSummary",
    ],
    "price_market": [
        "currentPrice", "previousClose", "open", "dayLow", "dayHigh",
        "regularMarketPreviousClose", "regularMarketOpen",
        "regularMarketDayLow", "regularMarketDayHigh",
        "regularMarketVolume", "volume", "averageVolume",
        "averageVolume10days", "marketCap",
        "fiftyTwoWeekLow", "fiftyTwoWeekHigh", "fiftyTwoWeekChange",
        "SandP52WeekChange", "fiftyDayAverage", "twoHundredDayAverage",
        "bid", "ask", "bidSize", "askSize",
        "priceToSalesTrailing12Months",
    ],
    "valuation": [
        "trailingPE", "forwardPE", "trailingEps", "forwardEps",
        "priceToBook", "bookValue",
        "enterpriseValue", "enterpriseToRevenue", "enterpriseToEbitda",
        "pegRatio",
    ],
    "dividends": [
        "dividendRate", "dividendYield", "exDividendDate", "payoutRatio",
        "fiveYearAvgDividendYield", "trailingAnnualDividendRate",
        "trailingAnnualDividendYield", "lastDividendValue", "lastDividendDate",
    ],
    "financials": [
        "totalRevenue", "revenuePerShare", "revenueGrowth",
        "grossMargins", "operatingMargins", "profitMargins", "ebitdaMargins",
        "netIncomeToCommon", "earningsGrowth", "earningsQuarterlyGrowth",
        "returnOnAssets", "returnOnEquity",
        "totalCash", "totalCashPerShare",
        "totalDebt", "debtToEquity",
        "currentRatio", "quickRatio",
        "operatingCashflow", "freeCashflow",
        "grossProfits", "ebitda",
    ],
    "shares_ownership": [
        "sharesOutstanding", "floatShares", "sharesShort",
        "sharesShortPriorMonth", "shortRatio", "shortPercentOfFloat",
        "heldPercentInsiders", "heldPercentInstitutions",
        "impliedSharesOutstanding",
    ],
    "analyst_targets": [
        "recommendationMean", "recommendationKey", "numberOfAnalystOpinions",
        "targetHighPrice", "targetLowPrice", "targetMeanPrice", "targetMedianPrice",
    ],
    "governance_risk": [
        "auditRisk", "boardRisk", "compensationRisk",
        "shareHolderRightsRisk", "overallRisk",
    ],
    "earnings_dates": [
        "mostRecentQuarter", "lastFiscalYearEnd", "nextFiscalYearEnd",
        "earningsTimestamp", "earningsTimestampStart", "earningsTimestampEnd",
    ],
}


def get_enhanced_stock_details(
    symbol: str,
    info_provider: StockInfoProvider,
    financials_provider: StockFinancialsProvider,
) -> str:
    """
    Return a comprehensive, normalised stock profile for a single ticker.

    Args:
        symbol:              A single stock ticker symbol (e.g. 'AAPL').
        info_provider:       Provides the info dict for the symbol.
        financials_provider: Provides financial statement data.

    Returns:
        A JSON string with the full stock profile grouped by category,
        or an error message if the symbol is invalid or data is unavailable.
    """
    logger.info(f"Fetching enhanced details for: {symbol}")
    sym = symbol.strip().upper()
    try:
        info = info_provider.get_info(sym)

        if not info.get("symbol"):
            return json.dumps(
                {"error": f"No data found for '{sym}'. Verify the symbol is correct."},
                indent=2,
            )

        # Build categorised info snapshot
        profile: Dict[str, Any] = {}
        for category, fields in INFO_FIELD_MAP.items():
            profile[category] = {f: info.get(f) for f in fields if info.get(f) is not None}

        # Financial statements helper
        def _stmt(getter_name: str) -> List[Dict[str, Any]]:
            try:
                df = getattr(financials_provider, getter_name)(sym)
                if df is None or df.empty:
                    return []
                return df_to_records(df.T)
            except Exception:
                return []

        profile["annual_income_statement"]    = _stmt("get_financials")
        profile["annual_balance_sheet"]       = _stmt("get_balance_sheet")
        profile["annual_cash_flow"]           = _stmt("get_cashflow")
        profile["quarterly_income_statement"] = _stmt("get_quarterly_financials")
        profile["quarterly_balance_sheet"]    = _stmt("get_quarterly_balance_sheet")
        profile["quarterly_cash_flow"]        = _stmt("get_quarterly_cashflow")

        # Analyst price targets
        try:
            apt = financials_provider.get_analyst_price_targets(sym)
            if apt is not None and not (hasattr(apt, "empty") and apt.empty):
                profile["analyst_price_targets"] = apt if isinstance(apt, dict) else apt.to_dict()
            else:
                profile["analyst_price_targets"] = {}
        except Exception:
            profile["analyst_price_targets"] = {}

        # Earnings calendar
        try:
            cal = financials_provider.get_calendar(sym)
            if cal is not None and not (hasattr(cal, "empty") and cal.empty):
                profile["earnings_calendar"] = cal if isinstance(cal, dict) else df_to_records(cal)
            else:
                profile["earnings_calendar"] = {}
        except Exception:
            profile["earnings_calendar"] = {}

        return json.dumps({sym: profile}, indent=2, default=str)

    except Exception as e:
        logger.error(f"Error fetching enhanced details for {sym}: {e}")
        return json.dumps(
            {"error": f"Failed to fetch enhanced details for '{sym}': {e}"}, indent=2
        )
