"""
Scoring primitives and declarative driver configuration.

Adding a new driver (OCP) is done by appending to DRIVER_CONFIGS without
modifying the scoring loop in finance/tools/drivers.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def score_metric(value: Optional[float], direction: str, thresholds: List[float]) -> int:
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


@dataclass
class DriverConfig:
    """Declarative specification for one investment driver."""

    rank: int
    name: str
    weight: float
    explanation: str
    # Each entry: (metric_label, info_key_or_None, direction, thresholds)
    # info_key_or_None=None means the value is computed externally and injected.
    sub_metrics: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DRIVER_CONFIGS — extend this list to add new drivers (OCP)
# ---------------------------------------------------------------------------

DRIVER_CONFIGS: List[DriverConfig] = [
    DriverConfig(
        rank=1,
        name="Valuation",
        weight=0.14,
        explanation=(
            "Measures how cheaply the stock is priced relative to earnings, book value, "
            "and enterprise value. Lower multiples indicate better value."
        ),
        sub_metrics=[
            {"label": "forwardPE",          "direction": "lower_better", "thresholds": [10, 15, 25, 40]},
            {"label": "priceToBook",        "direction": "lower_better", "thresholds": [1, 2, 4, 8]},
            {"label": "enterpriseToEbitda", "direction": "lower_better", "thresholds": [6, 10, 16, 25]},
        ],
    ),
    DriverConfig(
        rank=2,
        name="Growth",
        weight=0.14,
        explanation=(
            "Captures revenue and earnings expansion. A PEG ratio below 1 suggests "
            "the stock is undervalued relative to its growth rate."
        ),
        sub_metrics=[
            {"label": "revenueGrowth",  "direction": "higher_better", "thresholds": [0.0, 0.05, 0.15, 0.25]},
            {"label": "earningsGrowth", "direction": "higher_better", "thresholds": [0.0, 0.05, 0.15, 0.25]},
            {"label": "pegRatio",       "direction": "lower_better",  "thresholds": [0.5, 1.0, 1.5, 2.5]},
        ],
    ),
    DriverConfig(
        rank=3,
        name="Profitability",
        weight=0.12,
        explanation=(
            "Reflects how efficiently the company converts revenue into profit "
            "and generates returns for shareholders."
        ),
        sub_metrics=[
            {"label": "operatingMargins", "direction": "higher_better", "thresholds": [0.05, 0.10, 0.20, 0.30]},
            {"label": "profitMargins",    "direction": "higher_better", "thresholds": [0.03, 0.07, 0.15, 0.25]},
            {"label": "returnOnEquity",   "direction": "higher_better", "thresholds": [0.05, 0.10, 0.20, 0.30]},
        ],
    ),
    DriverConfig(
        rank=4,
        name="Financial Health",
        weight=0.12,
        explanation=(
            "Assesses balance-sheet strength, liquidity, and free-cash-flow generation. "
            "Strong health reduces bankruptcy and dilution risk."
        ),
        sub_metrics=[
            {"label": "debtToEquity", "direction": "lower_better",  "thresholds": [30, 60, 120, 200]},
            {"label": "currentRatio", "direction": "higher_better", "thresholds": [1.0, 1.5, 2.0, 3.0]},
            # fcfYield is computed externally and injected via the "computed" flag
            {"label": "freeCashflowYield", "direction": "higher_better", "thresholds": [0.01, 0.03, 0.05, 0.08], "computed": True},
        ],
    ),
    DriverConfig(
        rank=5,
        name="Price Momentum",
        weight=0.10,
        explanation=(
            "Tracks the stock's recent price trend relative to its 52-week range "
            "and key moving averages. Upward momentum often persists short-term."
        ),
        sub_metrics=[
            # All three are computed externally
            {"label": "fiftyTwoWeekPositionPct", "direction": "higher_better", "thresholds": [0.20, 0.40, 0.60, 0.80], "computed": True},
            {"label": "aboveFiftyDayMA",   "computed": True, "boolean": True},
            {"label": "aboveTwoHundredDayMA", "computed": True, "boolean": True},
        ],
    ),
    DriverConfig(
        rank=6,
        name="Analyst Sentiment",
        weight=0.12,
        explanation=(
            "Aggregates professional analyst ratings and price targets. "
            "A consensus 'Buy' with meaningful upside to the mean target is positive."
        ),
        sub_metrics=[
            {"label": "recommendationMean", "direction": "lower_better",  "thresholds": [1.5, 2.0, 2.5, 3.5]},
            {"label": "targetUpsidePct",    "direction": "higher_better", "thresholds": [0.0, 0.05, 0.15, 0.30], "computed": True},
        ],
    ),
    DriverConfig(
        rank=7,
        name="Dividend Quality",
        weight=0.08,
        explanation=(
            "Evaluates dividend attractiveness and sustainability. A moderate payout "
            "ratio (30-60%) with a decent yield signals reliable income."
        ),
        sub_metrics=[
            {"label": "dividendYield", "direction": "higher_better", "thresholds": [0.005, 0.015, 0.03, 0.05]},
            # payoutRatio has custom scoring logic; handled in drivers.py
            {"label": "payoutRatio", "computed": True, "custom_score": True},
        ],
    ),
    DriverConfig(
        rank=8,
        name="Earnings Quality",
        weight=0.08,
        explanation=(
            "Looks at whether EPS is growing and accelerating quarter over quarter. "
            "Rising forward EPS relative to trailing EPS signals improving earnings."
        ),
        sub_metrics=[
            {"label": "epsTrend",                "direction": "higher_better", "thresholds": [0.0, 0.05, 0.15, 0.25], "computed": True},
            {"label": "earningsQuarterlyGrowth", "direction": "higher_better", "thresholds": [0.0, 0.05, 0.15, 0.25]},
        ],
    ),
    DriverConfig(
        rank=9,
        name="Short Interest",
        weight=0.05,
        explanation=(
            "High short interest can be a headwind (bearish positioning) or "
            "set up a short squeeze. Lower short % of float is generally safer."
        ),
        sub_metrics=[
            {"label": "shortPercentOfFloat", "direction": "lower_better", "thresholds": [0.02, 0.05, 0.10, 0.20]},
        ],
    ),
    DriverConfig(
        rank=10,
        name="Institutional Support",
        weight=0.05,
        explanation=(
            "High institutional ownership signals professional confidence; "
            "meaningful insider ownership aligns management with shareholders."
        ),
        sub_metrics=[
            {"label": "heldPercentInstitutions", "direction": "higher_better", "thresholds": [0.30, 0.50, 0.65, 0.80]},
            {"label": "heldPercentInsiders",     "direction": "higher_better", "thresholds": [0.01, 0.05, 0.10, 0.20]},
        ],
    ),
]
