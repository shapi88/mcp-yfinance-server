"""
Data transformation utilities: safe type coercions and DataFrame/Series converters.
"""
import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def safe_float(value: Any) -> Optional[float]:
    """Return a JSON-safe float or None."""
    try:
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> Optional[int]:
    """Return a JSON-safe int or None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def df_to_records(df: Any) -> List[Dict[str, Any]]:
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
                entry[str(col)] = safe_float(val)
            elif isinstance(val, (int, np.integer)):
                # Also handle numpy integer types (e.g. int64) returned by pandas
                entry[str(col)] = int(val)
            else:
                entry[str(col)] = str(val)
        records.append(entry)
    return records


def series_to_records(series: Any) -> List[Dict[str, Any]]:
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
            entry["value"] = safe_float(val)
        else:
            entry["value"] = val
        records.append(entry)
    return records
