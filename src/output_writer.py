"""Output formatting, CSV generation, and schema validation module.
"""

import csv
import logging
from pathlib import Path
import re
from typing import Union, List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

EXACT_OUTPUT_COLUMNS = [
    "route",
    "week_of",
    "cost_per_tonne_km",
    "vs_own_history",
    "vs_similar_routes",
    "flagged",
    "matched_note_id",
    "reason"
]

VALID_FLAGGED_VALUES = {"Yes", "No (justified)", "No"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SchemaValidationError(Exception):
    """Raised when output CSV schema or content fails contract checks."""
    pass


def format_percentage_comparison(
    pct: Optional[float],
    comparison_type: str = "history"
) -> str:
    """Format numeric percentage into case study string representation.

    Args:
        pct: Numeric percentage (e.g. 35.52 or -2.31) or None
        comparison_type: "history" or "peer"

    Returns:
        Formatted string, e.g.:
        '+35.5% vs this route\'s past average'
        '+21.0% vs similar-length routes this week'
        'N/A (insufficient history)'
    """
    if pct is None or np.isnan(pct):
        if comparison_type == "history":
            return "N/A (insufficient history)"
        return "N/A (no peer routes)"

    sign = "+" if pct >= 0 else ""
    formatted_num = f"{sign}{pct:.1f}%"

    if comparison_type == "history":
        return f"{formatted_num} vs this route's past average"
    else:
        return f"{formatted_num} vs similar-length routes this week"


def format_output_dataframe(df_evaluated: pd.DataFrame) -> pd.DataFrame:
    """Format pipeline results into the exact output contract schema.

    Args:
        df_evaluated: DataFrame containing evaluated route-weeks with columns:
            - route
            - week_of
            - cost_per_tonne_km
            - vs_own_history_pct
            - vs_similar_routes_pct
            - is_numerical_anomaly
            - matched_note_id
            - reason

    Returns:
        pd.DataFrame sorted by (week_of, route) matching the exact schema.
    """
    df = df_evaluated.copy()

    # Deterministic sorting
    df = df.sort_values(["week_of", "route"]).reset_index(drop=True)

    formatted_rows = []
    for _, row in df.iterrows():
        # 1. cost_per_tonne_km: formatted with 2 decimal places consistently
        c = row["cost_per_tonne_km"]
        cost_str = f"{c:.2f}" if pd.notnull(c) else "0.00"

        # 2. vs_own_history
        vs_hist_str = format_percentage_comparison(row.get("vs_own_history_pct"), comparison_type="history")

        # 3. vs_similar_routes
        vs_peer_str = format_percentage_comparison(row.get("vs_similar_routes_pct"), comparison_type="peer")

        # 4. flagged verdict mapping:
        # - Yes: Anomaly detected and unexplained
        # - No (justified): Anomaly detected with verified supporting note
        # - No: No anomaly detected
        is_anomaly = bool(row.get("is_numerical_anomaly", False))
        matched_id = str(row.get("matched_note_id") or "").strip()

        if is_anomaly:
            if matched_id:
                flagged_str = "No (justified)"
            else:
                flagged_str = "Yes"
        else:
            flagged_str = "No"

        # 5. matched_note_id: exact ID when justified, blank when unexplained or not an anomaly
        note_id_str = matched_id if flagged_str == "No (justified)" else ""

        # 6. reason
        reason_str = str(row.get("reason") or "").strip()

        formatted_rows.append({
            "route": str(row["route"]).strip(),
            "week_of": str(row["week_of"]).strip(),
            "cost_per_tonne_km": cost_str,
            "vs_own_history": vs_hist_str,
            "vs_similar_routes": vs_peer_str,
            "flagged": flagged_str,
            "matched_note_id": note_id_str,
            "reason": reason_str
        })

    out_df = pd.DataFrame(formatted_rows, columns=EXACT_OUTPUT_COLUMNS)
    return out_df


def validate_output_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Strictly validate that a DataFrame satisfies the exact case study output contract.

    Checks:
    1. Exact column names and column order.
    2. Non-empty DataFrame.
    3. week_of format is YYYY-MM-DD.
    4. cost_per_tonne_km matches decimal float format.
    5. flagged is strictly one of 'Yes', 'No (justified)', 'No'.
    6. matched_note_id is non-empty iff flagged == 'No (justified)'.
    7. reason is non-empty.
    8. Deterministic sorting by (week_of, route).

    Returns:
        Tuple[bool, List[str]]: (is_valid, list of error messages)
    """
    errors = []

    # 1. Column names and order
    actual_cols = list(df.columns)
    if actual_cols != EXACT_OUTPUT_COLUMNS:
        errors.append(f"Column mismatch! Expected: {EXACT_OUTPUT_COLUMNS}, got: {actual_cols}")

    if df.empty:
        errors.append("Output DataFrame is empty!")
        return False, errors

    for idx, row in df.iterrows():
        # Date check
        w = str(row.get("week_of", ""))
        if not DATE_PATTERN.match(w):
            errors.append(f"Row {idx}: Invalid week_of format '{w}', expected YYYY-MM-DD")

        # Cost check
        c = str(row.get("cost_per_tonne_km", ""))
        try:
            float(c)
        except ValueError:
            errors.append(f"Row {idx}: Invalid cost_per_tonne_km '{c}'")

        # Flagged check
        flg = str(row.get("flagged", ""))
        if flg not in VALID_FLAGGED_VALUES:
            errors.append(f"Row {idx}: Invalid flagged value '{flg}'. Must be one of {VALID_FLAGGED_VALUES}")

        # Note ID consistency check
        nid = str(row.get("matched_note_id", "") or "").strip()
        if flg == "No (justified)" and not nid:
            errors.append(f"Row {idx}: Flagged as 'No (justified)' but matched_note_id is empty!")
        elif flg != "No (justified)" and nid:
            errors.append(f"Row {idx}: Flagged as '{flg}' but matched_note_id contains '{nid}' (should be blank)!")

        # Reason non-empty
        rsn = str(row.get("reason", "") or "").strip()
        if not rsn:
            errors.append(f"Row {idx}: Empty reason field!")

    # Check sorting
    sorted_df = df.sort_values(["week_of", "route"]).reset_index(drop=True)
    if not df.equals(sorted_df):
        errors.append("Rows are not deterministically sorted by (week_of, route)!")

    return len(errors) == 0, errors


def write_output_csv(df: pd.DataFrame, output_path: Union[str, Path]) -> Path:
    """Save the output DataFrame to CSV with RFC 4180 quoting and deterministic sorting.

    Args:
        df: Formatted output DataFrame
        output_path: Target CSV path

    Returns:
        Path: Resolved output path

    Raises:
        SchemaValidationError: If the DataFrame fails schema validation.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Validate before saving
    is_valid, errors = validate_output_schema(df)
    if not is_valid:
        raise SchemaValidationError(f"Cannot write invalid output CSV:\n" + "\n".join(errors[:10]))

    # Write using standard csv.QUOTE_MINIMAL to safely handle commas in reason strings
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
    logger.info(f"Successfully wrote {len(df)} rows to {path.resolve()}")
    return path
