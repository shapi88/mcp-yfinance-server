"""
Tool: get_top_stock_drivers

Identifies and scores the top 10 main drivers of a stock's investment case.
The scoring loop iterates over DRIVER_CONFIGS; new drivers are added by
extending that list (OCP — no changes here are needed).
"""
import json
import logging
from typing import Any, Dict, List, Optional

from finance.providers import StockInfoProvider
from finance.scoring import DRIVER_CONFIGS, score_metric
from finance.transformers import safe_float, safe_int

logger = logging.getLogger("mcp-yfinance-server")


def _payout_ratio_score(payout_ratio: Optional[float]) -> int:
    """Custom scoring for payout ratio: moderate (30-60%) is ideal."""
    if payout_ratio is None:
        return 0
    if 0.30 <= payout_ratio <= 0.60:
        return 4
    if 0 < payout_ratio < 0.30:
        return 3
    if 0.60 < payout_ratio <= 0.80:
        return 2
    if payout_ratio > 0.80:
        return 1
    return 0  # zero or negative payout


def _compute_driver_score(
    driver_name: str,
    sub_metrics: List[Dict[str, Any]],
    values: Dict[str, Any],
) -> int:
    """
    Compute the aggregate 0-4 score for a single driver.

    *values* is a flat dict mapping metric labels to their (pre-computed) values.
    """
    if driver_name == "Price Momentum":
        # Mixed boolean/numeric sub-metrics need special handling
        pos_pct = values.get("fiftyTwoWeekPositionPct")
        above_50 = values.get("aboveFiftyDayMA")
        above_200 = values.get("aboveTwoHundredDayMA")
        mom_52w = score_metric(pos_pct, "higher_better", [0.20, 0.40, 0.60, 0.80])
        mom_ma50 = 3 if above_50 else (1 if above_50 is not None else 0)
        mom_ma200 = 3 if above_200 else (1 if above_200 is not None else 0)
        raw = round((mom_52w + mom_ma50 + mom_ma200) / 3)
        return max(0, min(4, raw))

    scores = []
    for sm in sub_metrics:
        label = sm["label"]
        if sm.get("boolean"):
            continue  # handled above in Price Momentum
        if sm.get("custom_score"):
            # payoutRatio only
            scores.append(_payout_ratio_score(values.get(label)))
            continue
        val = values.get(label)
        scores.append(score_metric(val, sm["direction"], sm["thresholds"]))

    if not scores:
        return 0
    raw = round(sum(scores) / len(scores))
    return max(0, min(4, raw))


def get_top_stock_drivers(symbol: str, provider: StockInfoProvider) -> str:
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
        symbol:   A single stock ticker symbol (e.g. 'AAPL').
        provider: A StockInfoProvider used to retrieve data.

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
        info = provider.get_info(sym)

        if not info.get("symbol"):
            return json.dumps(
                {"error": f"No data found for '{sym}'. Verify the symbol is correct."},
                indent=2,
            )

        # ---- Extract metrics from info ----
        current_price       = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        forward_pe          = safe_float(info.get("forwardPE"))
        trailing_pe         = safe_float(info.get("trailingPE"))
        price_to_book       = safe_float(info.get("priceToBook"))
        ev_to_ebitda        = safe_float(info.get("enterpriseToEbitda"))
        peg_ratio           = safe_float(info.get("pegRatio"))
        revenue_growth      = safe_float(info.get("revenueGrowth"))
        earnings_growth     = safe_float(info.get("earningsGrowth"))
        earnings_qtr_growth = safe_float(info.get("earningsQuarterlyGrowth"))
        operating_margins   = safe_float(info.get("operatingMargins"))
        profit_margins      = safe_float(info.get("profitMargins"))
        roe                 = safe_float(info.get("returnOnEquity"))
        roa                 = safe_float(info.get("returnOnAssets"))
        debt_to_equity      = safe_float(info.get("debtToEquity"))
        current_ratio       = safe_float(info.get("currentRatio"))
        free_cashflow       = safe_float(info.get("freeCashflow"))
        market_cap          = safe_float(info.get("marketCap"))
        fifty2_low          = safe_float(info.get("fiftyTwoWeekLow"))
        fifty2_high         = safe_float(info.get("fiftyTwoWeekHigh"))
        ma50                = safe_float(info.get("fiftyDayAverage"))
        ma200               = safe_float(info.get("twoHundredDayAverage"))
        rec_mean            = safe_float(info.get("recommendationMean"))
        target_mean         = safe_float(info.get("targetMeanPrice"))
        num_analysts        = safe_int(info.get("numberOfAnalystOpinions"))
        dividend_yield      = safe_float(info.get("dividendYield"))
        payout_ratio        = safe_float(info.get("payoutRatio"))
        trailing_eps        = safe_float(info.get("trailingEps"))
        forward_eps         = safe_float(info.get("forwardEps"))
        short_pct_float     = safe_float(info.get("shortPercentOfFloat"))
        held_pct_inst       = safe_float(info.get("heldPercentInstitutions"))
        held_pct_insider    = safe_float(info.get("heldPercentInsiders"))

        # ---- Derived / computed metrics ----
        fcf_yield: Optional[float] = (
            (free_cashflow / market_cap)
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

        # Use forward P/E; fall back to trailing P/E for valuation scoring
        pe = forward_pe if forward_pe is not None else trailing_pe

        # Flat value map used by _compute_driver_score
        values: Dict[str, Any] = {
            "forwardPE":               pe,
            "priceToBook":             price_to_book,
            "enterpriseToEbitda":      ev_to_ebitda,
            "revenueGrowth":           revenue_growth,
            "earningsGrowth":          earnings_growth,
            "pegRatio":                peg_ratio,
            "operatingMargins":        operating_margins,
            "profitMargins":           profit_margins,
            "returnOnEquity":          roe,
            "debtToEquity":            debt_to_equity,
            "currentRatio":            current_ratio,
            "freeCashflowYield":       fcf_yield,
            "fiftyTwoWeekPositionPct": price_vs_52w_range,
            "aboveFiftyDayMA":         above_ma50,
            "aboveTwoHundredDayMA":    above_ma200,
            "recommendationMean":      rec_mean,
            "targetUpsidePct":         target_upside,
            "dividendYield":           dividend_yield,
            "payoutRatio":             payout_ratio,
            "epsTrend":                eps_growth_trend,
            "earningsQuarterlyGrowth": earnings_qtr_growth,
            "shortPercentOfFloat":     short_pct_float,
            "heldPercentInstitutions": held_pct_inst,
            "heldPercentInsiders":     held_pct_insider,
        }

        # ---- Build driver list from DRIVER_CONFIGS ----
        drivers = []
        for cfg in DRIVER_CONFIGS:
            driver_score = _compute_driver_score(cfg.name, cfg.sub_metrics, values)

            # Assemble per-driver raw metrics for transparency
            if cfg.name == "Valuation":
                raw_metrics: Dict[str, Any] = {
                    "forwardPE": forward_pe, "trailingPE": trailing_pe,
                    "priceToBook": price_to_book, "enterpriseToEbitda": ev_to_ebitda,
                }
            elif cfg.name == "Growth":
                raw_metrics = {
                    "revenueGrowth": revenue_growth,
                    "earningsGrowth": earnings_growth,
                    "pegRatio": peg_ratio,
                }
            elif cfg.name == "Profitability":
                raw_metrics = {
                    "operatingMargins": operating_margins,
                    "profitMargins": profit_margins,
                    "returnOnEquity": roe,
                    "returnOnAssets": roa,
                }
            elif cfg.name == "Financial Health":
                raw_metrics = {
                    "debtToEquity": debt_to_equity,
                    "currentRatio": current_ratio,
                    "freeCashflow": free_cashflow,
                    "freeCashflowYield": fcf_yield,
                }
            elif cfg.name == "Price Momentum":
                raw_metrics = {
                    "currentPrice": current_price,
                    "fiftyTwoWeekPositionPct": price_vs_52w_range,
                    "aboveFiftyDayMA": above_ma50,
                    "aboveTwoHundredDayMA": above_ma200,
                }
            elif cfg.name == "Analyst Sentiment":
                raw_metrics = {
                    "recommendationMean": rec_mean,
                    "recommendationKey": info.get("recommendationKey"),
                    "numberOfAnalystOpinions": num_analysts,
                    "targetMeanPrice": target_mean,
                    "targetUpsidePct": target_upside,
                }
            elif cfg.name == "Dividend Quality":
                raw_metrics = {
                    "dividendYield": dividend_yield,
                    "payoutRatio": payout_ratio,
                    "fiveYearAvgDividendYield": safe_float(info.get("fiveYearAvgDividendYield")),
                }
            elif cfg.name == "Earnings Quality":
                raw_metrics = {
                    "trailingEps": trailing_eps,
                    "forwardEps": forward_eps,
                    "epsTrend": eps_growth_trend,
                    "earningsQuarterlyGrowth": earnings_qtr_growth,
                }
            elif cfg.name == "Short Interest":
                raw_metrics = {
                    "shortPercentOfFloat": short_pct_float,
                    "sharesShort": safe_int(info.get("sharesShort")),
                    "shortRatio": safe_float(info.get("shortRatio")),
                }
            else:  # Institutional Support
                raw_metrics = {
                    "heldPercentInstitutions": held_pct_inst,
                    "heldPercentInsiders": held_pct_insider,
                }

            drivers.append({
                "rank": cfg.rank,
                "driver": cfg.name,
                "score": driver_score,
                "weight": cfg.weight,
                "metrics": raw_metrics,
                "explanation": cfg.explanation,
            })

        # ---- Weighted aggregate ----
        total_weighted = 0.0
        for d in drivers:
            d["weighted_score"] = round(d["score"] * d["weight"], 4)
            total_weighted += d["weighted_score"]

        max_possible = 4.0 * sum(d["weight"] for d in drivers)
        overall_score = round((total_weighted / max_possible) * 4, 2) if max_possible > 0 else 0.0

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
        return json.dumps(
            {"error": f"Failed to compute drivers for '{sym}': {e}"}, indent=2
        )
