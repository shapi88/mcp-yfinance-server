import json
import logging
import math
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-yfinance-server")

# Initialize FastMCP server
mcp = FastMCP("Advanced-Finance-Server")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> Optional[float]:
    """Return a JSON-safe float or None."""
    try:
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Return a JSON-safe int or None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _df_to_records(df: Any) -> List[Dict[str, Any]]:
    """Convert a DataFrame (date-indexed) to a list of JSON-safe dicts."""
    if df is None or (hasattr(df, "empty") and df.empty):
        return []
    records: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        entry: Dict[str, Any] = {"date": str(idx)[:10]}
        for col in df.columns:
            val = row[col]
            try:
                if pd.isna(val):
                    entry[str(col)] = None
                    continue
            except (TypeError, ValueError):
                pass
            if isinstance(val, float):
                entry[str(col)] = _safe_float(val)
            elif isinstance(val, int):
                entry[str(col)] = val
            else:
                entry[str(col)] = str(val)
        records.append(entry)
    return records


def _series_to_records(series: Any) -> List[Dict[str, Any]]:
    """Convert a Series to a list of {date, value} JSON-safe dicts."""
    if series is None or (hasattr(series, "empty") and series.empty):
        return []
    records: List[Dict[str, Any]] = []
    for idx, val in series.items():
        entry: Dict[str, Any] = {"date": str(idx)[:10]}
        try:
            is_na = pd.isna(val)
        except (TypeError, ValueError):
            is_na = False
        if is_na:
            entry["value"] = None
        elif isinstance(val, float):
            entry["value"] = _safe_float(val)
        else:
            entry["value"] = val
        records.append(entry)
    return records


# ---------------------------------------------------------------------------
# Categorised field map for get_enhanced_stock_details
# Only non-deprecated yfinance >=0.2.x info fields are listed.
# ---------------------------------------------------------------------------
_INFO_FIELD_MAP: Dict[str, List[str]] = {
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

@mcp.tool()
def get_advanced_stock_metrics(tickers: str) -> str:
    """
    Fetch comprehensive stock data and key metrics for one or more ticker symbols.
    
    This tool retrieves basic info, growth potential, valuation, profitability,
    and financial health metrics from Yahoo Finance to help evaluate the stock's future potential.
    
    Args:
        tickers: A comma-separated list of stock ticker symbols (e.g., 'AAPL' or 'AAPL, MSFT, TSLA').
        
    Returns:
        A JSON string mapping each ticker symbol to its retrieved metrics or error message.
    """
    logger.info(f"Fetching advanced metrics for tickers: {tickers}")
    try:
        # Split by comma and clean up whitespace
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        if not ticker_list:
            return json.dumps({"error": "Ticker list cannot be empty. Please provide at least one valid ticker symbol."}, indent=2)
            
        results = {}
        
        for ticker in ticker_list:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # yfinance returns info dict, but if ticker is invalid or has no data, info might be empty or missing key fields like symbol
                if not info or not isinstance(info, dict) or not info.get("symbol"):
                    results[ticker] = {"error": f"No data found for ticker '{ticker}'. Please verify the symbol is correct."}
                    continue
                    
                # Extract the requested metrics safely using .get()
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
                    }
                }
            except Exception as e:
                logger.error(f"Error fetching data for ticker {ticker}: {str(e)}")
                results[ticker] = {"error": f"An error occurred while fetching metrics: {str(e)}"}
                
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Error processing tickers string '{tickers}': {str(e)}")
        return json.dumps({"error": f"An error occurred while processing tickers: {str(e)}"}, indent=2)


# ---------------------------------------------------------------------------
# Tool: get_enhanced_stock_details
# ---------------------------------------------------------------------------

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
    logger.info(f"Fetching enhanced details for: {symbol}")
    sym = symbol.strip().upper()
    try:
        stock = yf.Ticker(sym)
        info = stock.info or {}

        if not info.get("symbol"):
            return json.dumps(
                {"error": f"No data found for '{sym}'. Verify the symbol is correct."},
                indent=2,
            )

        # Build categorised info snapshot
        profile: Dict[str, Any] = {}
        for category, fields in _INFO_FIELD_MAP.items():
            profile[category] = {f: info.get(f) for f in fields if info.get(f) is not None}

        # Annual financial statements (transposed: date as index)
        def _stmt(attr: str) -> List[Dict[str, Any]]:
            try:
                df = getattr(stock, attr)
                if df is None or df.empty:
                    return []
                return _df_to_records(df.T)
            except Exception:
                return []

        profile["annual_income_statement"] = _stmt("financials")
        profile["annual_balance_sheet"] = _stmt("balance_sheet")
        profile["annual_cash_flow"] = _stmt("cashflow")
        profile["quarterly_income_statement"] = _stmt("quarterly_financials")
        profile["quarterly_balance_sheet"] = _stmt("quarterly_balance_sheet")
        profile["quarterly_cash_flow"] = _stmt("quarterly_cashflow")

        # Analyst price targets
        try:
            apt = stock.analyst_price_targets
            if apt is not None and not (hasattr(apt, "empty") and apt.empty):
                profile["analyst_price_targets"] = apt if isinstance(apt, dict) else apt.to_dict()
            else:
                profile["analyst_price_targets"] = {}
        except Exception:
            profile["analyst_price_targets"] = {}

        # Earnings calendar
        try:
            cal = stock.calendar
            if cal is not None and not (hasattr(cal, "empty") and cal.empty):
                profile["earnings_calendar"] = cal if isinstance(cal, dict) else _df_to_records(cal)
            else:
                profile["earnings_calendar"] = {}
        except Exception:
            profile["earnings_calendar"] = {}

        return json.dumps({sym: profile}, indent=2, default=str)

    except Exception as e:
        logger.error(f"Error fetching enhanced details for {sym}: {e}")
        return json.dumps({"error": f"Failed to fetch enhanced details for '{sym}': {e}"}, indent=2)


# ---------------------------------------------------------------------------
# Tool: get_stock_5y_history
# ---------------------------------------------------------------------------

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
    logger.info(f"Fetching 5-year history for: {symbol}")
    sym = symbol.strip().upper()
    try:
        stock = yf.Ticker(sym)

        result: Dict[str, Any] = {"symbol": sym}

        # --- Price / volume (weekly, 5 years) ---
        try:
            hist = stock.history(period="5y", interval="1wk")
            if hist is not None and not hist.empty:
                price_records = []
                for idx, row in hist.iterrows():
                    price_records.append({
                        "date": str(idx)[:10],
                        "open": _safe_float(row.get("Open")),
                        "high": _safe_float(row.get("High")),
                        "low": _safe_float(row.get("Low")),
                        "close": _safe_float(row.get("Close")),
                        "volume": _safe_int(row.get("Volume")),
                        "dividends": _safe_float(row.get("Dividends", 0)),
                        "stock_splits": _safe_float(row.get("Stock Splits", 0)),
                    })
                result["price_history_weekly"] = price_records
            else:
                result["price_history_weekly"] = []
        except Exception as e:
            logger.warning(f"price_history unavailable for {sym}: {e}")
            result["price_history_weekly"] = []

        # --- Dividends ---
        try:
            divs = stock.dividends
            result["dividends"] = _series_to_records(divs)
        except Exception:
            result["dividends"] = []

        # --- Stock splits ---
        try:
            splits = stock.splits
            result["stock_splits"] = _series_to_records(splits)
        except Exception:
            result["stock_splits"] = []

        # --- Annual financial statements ---
        def _annual_stmt(attr: str, label: str) -> None:
            try:
                df = getattr(stock, attr)
                result[label] = _df_to_records(df.T) if (df is not None and not df.empty) else []
            except Exception as e:
                logger.warning(f"{label} unavailable for {sym}: {e}")
                result[label] = []

        _annual_stmt("financials", "annual_income_statement")
        _annual_stmt("balance_sheet", "annual_balance_sheet")
        _annual_stmt("cashflow", "annual_cash_flow")

        # --- Quarterly financial statements ---
        _annual_stmt("quarterly_financials", "quarterly_income_statement")
        _annual_stmt("quarterly_balance_sheet", "quarterly_balance_sheet")
        _annual_stmt("quarterly_cashflow", "quarterly_cash_flow")

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"Error fetching 5y history for {sym}: {e}")
        return json.dumps({"error": f"Failed to fetch 5-year history for '{sym}': {e}"}, indent=2)


# ---------------------------------------------------------------------------
# Tool: get_top_stock_drivers
# ---------------------------------------------------------------------------

def _score_metric(value: Optional[float], direction: str, thresholds: List[float]) -> int:
    """
    Score a metric on a 0-4 scale using provided thresholds.

    direction='higher_better'  → value >= thresholds[3] → 4, etc.
    direction='lower_better'   → value <= thresholds[0] → 4, etc.

    thresholds must have exactly 4 elements: [worst, below_avg, above_avg, best].
    Returns 0 if value is None.

    Raises:
        ValueError: If thresholds does not have exactly 4 elements.
    """
    if len(thresholds) != 4:
        raise ValueError(f"thresholds must have exactly 4 elements, got {len(thresholds)}")
    if value is None:
        return 0
    t = thresholds  # [worst, below_avg, above_avg, best]
    if direction == "higher_better":
        if value >= t[3]:
            return 4
        if value >= t[2]:
            return 3
        if value >= t[1]:
            return 2
        if value >= t[0]:
            return 1
        return 0
    else:  # lower_better
        if value <= t[0]:
            return 4
        if value <= t[1]:
            return 3
        if value <= t[2]:
            return 2
        if value <= t[3]:
            return 1
        return 0


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
    logger.info(f"Computing stock drivers for: {symbol}")
    sym = symbol.strip().upper()
    try:
        stock = yf.Ticker(sym)
        info = stock.info or {}

        if not info.get("symbol"):
            return json.dumps(
                {"error": f"No data found for '{sym}'. Verify the symbol is correct."},
                indent=2,
            )

        # ---- Retrieve metrics ----
        current_price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        forward_pe = _safe_float(info.get("forwardPE"))
        trailing_pe = _safe_float(info.get("trailingPE"))
        price_to_book = _safe_float(info.get("priceToBook"))
        ev_to_ebitda = _safe_float(info.get("enterpriseToEbitda"))
        peg_ratio = _safe_float(info.get("pegRatio"))
        revenue_growth = _safe_float(info.get("revenueGrowth"))
        earnings_growth = _safe_float(info.get("earningsGrowth"))
        earnings_quarterly_growth = _safe_float(info.get("earningsQuarterlyGrowth"))
        operating_margins = _safe_float(info.get("operatingMargins"))
        profit_margins = _safe_float(info.get("profitMargins"))
        roe = _safe_float(info.get("returnOnEquity"))
        roa = _safe_float(info.get("returnOnAssets"))
        debt_to_equity = _safe_float(info.get("debtToEquity"))
        current_ratio = _safe_float(info.get("currentRatio"))
        free_cashflow = _safe_float(info.get("freeCashflow"))
        market_cap = _safe_float(info.get("marketCap"))
        fifty2_low = _safe_float(info.get("fiftyTwoWeekLow"))
        fifty2_high = _safe_float(info.get("fiftyTwoWeekHigh"))
        ma50 = _safe_float(info.get("fiftyDayAverage"))
        ma200 = _safe_float(info.get("twoHundredDayAverage"))
        rec_mean = _safe_float(info.get("recommendationMean"))  # 1=Strong Buy…5=Sell
        target_mean = _safe_float(info.get("targetMeanPrice"))
        num_analysts = _safe_int(info.get("numberOfAnalystOpinions"))
        dividend_yield = _safe_float(info.get("dividendYield"))
        payout_ratio = _safe_float(info.get("payoutRatio"))
        trailing_eps = _safe_float(info.get("trailingEps"))
        forward_eps = _safe_float(info.get("forwardEps"))
        short_pct_float = _safe_float(info.get("shortPercentOfFloat"))
        held_pct_inst = _safe_float(info.get("heldPercentInstitutions"))
        held_pct_insider = _safe_float(info.get("heldPercentInsiders"))

        # Derived
        fcf_yield = (
            (_safe_float(free_cashflow) / _safe_float(market_cap))
            if (free_cashflow and market_cap and market_cap > 0)
            else None
        )
        price_vs_52w_range: Optional[float] = None
        if fifty2_low is not None and fifty2_high is not None and fifty2_high > fifty2_low:
            price_vs_52w_range = (
                (current_price - fifty2_low) / (fifty2_high - fifty2_low)
                if current_price is not None
                else None
            )
        above_ma50: Optional[bool] = (
            (current_price > ma50) if (current_price is not None and ma50 is not None) else None
        )
        above_ma200: Optional[bool] = (
            (current_price > ma200) if (current_price is not None and ma200 is not None) else None
        )
        target_upside: Optional[float] = (
            (target_mean - current_price) / current_price
            if (target_mean is not None and current_price and current_price > 0)
            else None
        )
        eps_growth_trend: Optional[float] = (
            (forward_eps - trailing_eps) / abs(trailing_eps)
            if (forward_eps is not None and trailing_eps and trailing_eps != 0)
            else None
        )

        # ---- Score each driver ----

        # 1. Valuation (lower PE/PB/EV_EBITDA = better)
        pe = forward_pe if forward_pe is not None else trailing_pe
        val_pe_score = _score_metric(pe, "lower_better", [10, 15, 25, 40])
        val_pb_score = _score_metric(price_to_book, "lower_better", [1, 2, 4, 8])
        val_ev_score = _score_metric(ev_to_ebitda, "lower_better", [6, 10, 16, 25])
        valuation_score = round((val_pe_score + val_pb_score + val_ev_score) / 3)
        valuation_score = max(0, min(4, valuation_score))

        # 2. Growth
        rev_g_score = _score_metric(revenue_growth, "higher_better", [0.0, 0.05, 0.15, 0.25])
        earn_g_score = _score_metric(earnings_growth, "higher_better", [0.0, 0.05, 0.15, 0.25])
        peg_score = _score_metric(peg_ratio, "lower_better", [0.5, 1.0, 1.5, 2.5]) if peg_ratio is not None else 0
        growth_score = round((rev_g_score + earn_g_score + peg_score) / 3)
        growth_score = max(0, min(4, growth_score))

        # 3. Profitability
        op_m_score = _score_metric(operating_margins, "higher_better", [0.05, 0.10, 0.20, 0.30])
        net_m_score = _score_metric(profit_margins, "higher_better", [0.03, 0.07, 0.15, 0.25])
        roe_score = _score_metric(roe, "higher_better", [0.05, 0.10, 0.20, 0.30])
        profitability_score = round((op_m_score + net_m_score + roe_score) / 3)
        profitability_score = max(0, min(4, profitability_score))

        # 4. Financial Health
        de_score = _score_metric(debt_to_equity, "lower_better", [30, 60, 120, 200])
        cr_score = _score_metric(current_ratio, "higher_better", [1.0, 1.5, 2.0, 3.0])
        fcf_score = _score_metric(fcf_yield, "higher_better", [0.01, 0.03, 0.05, 0.08])
        health_score = round((de_score + cr_score + fcf_score) / 3)
        health_score = max(0, min(4, health_score))

        # 5. Price Momentum
        mom_52w_score = _score_metric(price_vs_52w_range, "higher_better", [0.20, 0.40, 0.60, 0.80])
        mom_ma50 = 3 if above_ma50 else (1 if above_ma50 is not None else 0)
        mom_ma200 = 3 if above_ma200 else (1 if above_ma200 is not None else 0)
        momentum_score = round((mom_52w_score + mom_ma50 + mom_ma200) / 3)
        momentum_score = max(0, min(4, momentum_score))

        # 6. Analyst Sentiment (rec_mean: 1=Strong Buy, 5=Sell → lower is better)
        analyst_rec_score = _score_metric(rec_mean, "lower_better", [1.5, 2.0, 2.5, 3.5])
        analyst_upside_score = _score_metric(target_upside, "higher_better", [0.0, 0.05, 0.15, 0.30])
        analyst_score = round((analyst_rec_score + analyst_upside_score) / 2)
        analyst_score = max(0, min(4, analyst_score))

        # 7. Dividend Quality
        div_yield_score = _score_metric(dividend_yield, "higher_better", [0.005, 0.015, 0.03, 0.05])
        # Payout ratio scoring: moderate (30-60%) is ideal; very high (>80%) is risky
        if payout_ratio is None:
            pr_score = 0
        elif 0.30 <= payout_ratio <= 0.60:
            pr_score = 4  # Sustainable and generous
        elif 0 < payout_ratio < 0.30:
            pr_score = 3  # Conservative but growing
        elif 0.60 < payout_ratio <= 0.80:
            pr_score = 2  # Elevated but manageable
        elif payout_ratio > 0.80:
            pr_score = 1  # Unsustainably high
        else:
            pr_score = 0  # Zero or negative payout
        dividend_score = round((div_yield_score + pr_score) / 2)
        dividend_score = max(0, min(4, dividend_score))

        # 8. Earnings Quality
        eps_trend_score = _score_metric(eps_growth_trend, "higher_better", [0.0, 0.05, 0.15, 0.25])
        qtr_earn_score = _score_metric(
            earnings_quarterly_growth, "higher_better", [0.0, 0.05, 0.15, 0.25]
        )
        earnings_score = round((eps_trend_score + qtr_earn_score) / 2)
        earnings_score = max(0, min(4, earnings_score))

        # 9. Short Interest (lower short % = less headwind)
        short_score = _score_metric(short_pct_float, "lower_better", [0.02, 0.05, 0.10, 0.20])

        # 10. Institutional Support
        inst_score = _score_metric(held_pct_inst, "higher_better", [0.30, 0.50, 0.65, 0.80])
        insider_score = _score_metric(held_pct_insider, "higher_better", [0.01, 0.05, 0.10, 0.20])
        institutional_score = round((inst_score + insider_score) / 2)
        institutional_score = max(0, min(4, institutional_score))

        # ---- Weighted aggregate ----
        drivers = [
            {
                "rank": 1,
                "driver": "Valuation",
                "score": valuation_score,
                "weight": 0.14,
                "metrics": {
                    "forwardPE": forward_pe,
                    "trailingPE": trailing_pe,
                    "priceToBook": price_to_book,
                    "enterpriseToEbitda": ev_to_ebitda,
                },
                "explanation": (
                    "Measures how cheaply the stock is priced relative to earnings, book value, "
                    "and enterprise value. Lower multiples indicate better value."
                ),
            },
            {
                "rank": 2,
                "driver": "Growth",
                "score": growth_score,
                "weight": 0.14,
                "metrics": {
                    "revenueGrowth": revenue_growth,
                    "earningsGrowth": earnings_growth,
                    "pegRatio": peg_ratio,
                },
                "explanation": (
                    "Captures revenue and earnings expansion. A PEG ratio below 1 suggests "
                    "the stock is undervalued relative to its growth rate."
                ),
            },
            {
                "rank": 3,
                "driver": "Profitability",
                "score": profitability_score,
                "weight": 0.12,
                "metrics": {
                    "operatingMargins": operating_margins,
                    "profitMargins": profit_margins,
                    "returnOnEquity": roe,
                    "returnOnAssets": roa,
                },
                "explanation": (
                    "Reflects how efficiently the company converts revenue into profit "
                    "and generates returns for shareholders."
                ),
            },
            {
                "rank": 4,
                "driver": "Financial Health",
                "score": health_score,
                "weight": 0.12,
                "metrics": {
                    "debtToEquity": debt_to_equity,
                    "currentRatio": current_ratio,
                    "freeCashflow": free_cashflow,
                    "freeCashflowYield": fcf_yield,
                },
                "explanation": (
                    "Assesses balance-sheet strength, liquidity, and free-cash-flow generation. "
                    "Strong health reduces bankruptcy and dilution risk."
                ),
            },
            {
                "rank": 5,
                "driver": "Price Momentum",
                "score": momentum_score,
                "weight": 0.10,
                "metrics": {
                    "currentPrice": current_price,
                    "fiftyTwoWeekPositionPct": price_vs_52w_range,
                    "aboveFiftyDayMA": above_ma50,
                    "aboveTwoHundredDayMA": above_ma200,
                },
                "explanation": (
                    "Tracks the stock's recent price trend relative to its 52-week range "
                    "and key moving averages. Upward momentum often persists short-term."
                ),
            },
            {
                "rank": 6,
                "driver": "Analyst Sentiment",
                "score": analyst_score,
                "weight": 0.12,
                "metrics": {
                    "recommendationMean": rec_mean,
                    "recommendationKey": info.get("recommendationKey"),
                    "numberOfAnalystOpinions": num_analysts,
                    "targetMeanPrice": target_mean,
                    "targetUpsidePct": target_upside,
                },
                "explanation": (
                    "Aggregates professional analyst ratings and price targets. "
                    "A consensus 'Buy' with meaningful upside to the mean target is positive."
                ),
            },
            {
                "rank": 7,
                "driver": "Dividend Quality",
                "score": dividend_score,
                "weight": 0.08,
                "metrics": {
                    "dividendYield": dividend_yield,
                    "payoutRatio": payout_ratio,
                    "fiveYearAvgDividendYield": _safe_float(info.get("fiveYearAvgDividendYield")),
                },
                "explanation": (
                    "Evaluates dividend attractiveness and sustainability. A moderate payout "
                    "ratio (30-60%) with a decent yield signals reliable income."
                ),
            },
            {
                "rank": 8,
                "driver": "Earnings Quality",
                "score": earnings_score,
                "weight": 0.08,
                "metrics": {
                    "trailingEps": trailing_eps,
                    "forwardEps": forward_eps,
                    "epsTrend": eps_growth_trend,
                    "earningsQuarterlyGrowth": earnings_quarterly_growth,
                },
                "explanation": (
                    "Looks at whether EPS is growing and accelerating quarter over quarter. "
                    "Rising forward EPS relative to trailing EPS signals improving earnings."
                ),
            },
            {
                "rank": 9,
                "driver": "Short Interest",
                "score": short_score,
                "weight": 0.05,
                "metrics": {
                    "shortPercentOfFloat": short_pct_float,
                    "sharesShort": _safe_int(info.get("sharesShort")),
                    "shortRatio": _safe_float(info.get("shortRatio")),
                },
                "explanation": (
                    "High short interest can be a headwind (bearish positioning) or "
                    "set up a short squeeze. Lower short % of float is generally safer."
                ),
            },
            {
                "rank": 10,
                "driver": "Institutional Support",
                "score": institutional_score,
                "weight": 0.05,
                "metrics": {
                    "heldPercentInstitutions": held_pct_inst,
                    "heldPercentInsiders": held_pct_insider,
                },
                "explanation": (
                    "High institutional ownership signals professional confidence; "
                    "meaningful insider ownership aligns management with shareholders."
                ),
            },
        ]

        # Compute weighted scores and sort by weighted contribution
        total_weighted = 0.0
        for d in drivers:
            d["weighted_score"] = round(d["score"] * d["weight"], 4)
            total_weighted += d["weighted_score"]

        # Overall score scaled back to 0-4
        max_possible = 4.0 * sum(d["weight"] for d in drivers)
        overall_score = round((total_weighted / max_possible) * 4, 2) if max_possible > 0 else 0.0

        # Signal
        if overall_score >= 3.2:
            signal = "Strong Buy"
        elif overall_score >= 2.4:
            signal = "Buy"
        elif overall_score >= 1.6:
            signal = "Hold"
        elif overall_score >= 0.8:
            signal = "Sell"
        else:
            signal = "Strong Sell"

        result = {
            "symbol": sym,
            "overall_score": overall_score,
            "signal": signal,
            "score_scale": "0 (weakest) to 4 (strongest)",
            "drivers": sorted(drivers, key=lambda x: x["weighted_score"], reverse=True),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        logger.error(f"Error computing drivers for {sym}: {e}")
        return json.dumps({"error": f"Failed to compute drivers for '{sym}': {e}"}, indent=2)


if __name__ == "__main__":
    mcp.run()
