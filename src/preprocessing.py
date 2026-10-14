"""Data preprocessing and route normalization module.
"""

import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def preprocess_shipments(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Clean, parse, validate and normalize raw shipment records.

    Performs:
    1. Type casting for numerical columns (`quantity_tonnes`, `distance_km`, `freight_cost_inr`).
    2. Date parsing for `shipment_date` (ISO `YYYY-MM-DD`).
    3. Route normalization: `route = f"{origin.strip()}-{destination.strip()}"`.
    4. Business rule validation:
       - quantity_tonnes > 0
       - distance_km > 0
       - freight_cost_inr >= 0
    5. Route type normalization: Short, Medium, Long (preserves provided route_type).
    6. Calculation of shipment-level tonne_km for auditing.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: Clean DataFrame and audit report.
    """
    df = df_raw.copy()
    audit_report: Dict[str, Any] = {
        "initial_row_count": len(df),
        "invalid_numeric_rows": 0,
        "invalid_quantity_rows": 0,
        "invalid_distance_rows": 0,
        "invalid_cost_rows": 0,
        "routes_found": [],
        "route_types_found": [],
        "date_range": ()
    }

    # 1. Type casting
    numeric_cols = ["quantity_tonnes", "distance_km", "freight_cost_inr"]
    for col in numeric_cols:
        orig_nulls = df[col].isnull().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        new_nulls = df[col].isnull().sum() - orig_nulls
        if new_nulls > 0:
            audit_report["invalid_numeric_rows"] += int(new_nulls)
            raise ValueError(f"Found {new_nulls} unparseable non-numeric values in column {col}")

    # 2. Date parsing
    df["shipment_date"] = pd.to_datetime(df["shipment_date"], errors="coerce")
    if df["shipment_date"].isnull().any():
        bad_dates = df_raw.loc[df["shipment_date"].isnull(), "shipment_date"].tolist()
        raise ValueError(f"Found invalid dates in shipment_date: {bad_dates[:5]}")

    # 3. Value range checks
    invalid_qty = (df["quantity_tonnes"] <= 0).sum()
    invalid_dist = (df["distance_km"] <= 0).sum()
    invalid_cost = (df["freight_cost_inr"] < 0).sum()

    audit_report["invalid_quantity_rows"] = int(invalid_qty)
    audit_report["invalid_distance_rows"] = int(invalid_dist)
    audit_report["invalid_cost_rows"] = int(invalid_cost)

    if invalid_qty > 0 or invalid_dist > 0 or invalid_cost > 0:
        raise ValueError(
            f"Data-quality failure: invalid quantities ({invalid_qty}), "
            f"distances ({invalid_dist}), or freight costs ({invalid_cost})"
        )

    # 4. Route normalization: origin and destination fields (without merging opposite directions)
    df["origin"] = df["origin"].astype(str).str.strip()
    df["destination"] = df["destination"].astype(str).str.strip()
    df["route"] = df["origin"] + "-" + df["destination"]

    # 5. Route type normalization
    df["route_type"] = df["route_type"].astype(str).str.strip()

    # 6. Tonne-km per shipment
    df["tonne_km"] = df["quantity_tonnes"] * df["distance_km"]

    # Audit summary
    audit_report["final_row_count"] = len(df)
    audit_report["routes_found"] = sorted(df["route"].unique().tolist())
    audit_report["route_types_found"] = sorted(df["route_type"].unique().tolist())
    audit_report["date_range"] = (
        df["shipment_date"].min().strftime("%Y-%m-%d"),
        df["shipment_date"].max().strftime("%Y-%m-%d")
    )

    logger.info(
        f"Preprocessing complete: {len(df)} records valid across {len(audit_report['routes_found'])} routes "
        f"spanning {audit_report['date_range'][0]} to {audit_report['date_range'][1]}."
    )
    return df, audit_report
