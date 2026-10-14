"""Weekly grouping and aggregate cost-per-tonne-km calculation.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def assign_monday_week(series: pd.Series) -> pd.Series:
    """Assign dates to their Monday-starting ISO week date (YYYY-MM-DD).

    Weeks run Monday through Sunday. The week identifier is the Monday date.

    Example:
        2024-01-01 (Monday) -> '2024-01-01'
        2024-01-07 (Sunday) -> '2024-01-01'
        2024-01-08 (Monday) -> '2024-01-08'
    """
    dt = pd.to_datetime(series)
    # subtracting day of week (Monday is 0, Sunday is 6)
    monday = dt - pd.to_timedelta(dt.dt.weekday, unit="D")
    return monday.dt.strftime("%Y-%m-%d")


def aggregate_weekly_costs(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Group shipments by route, route_type, and Monday-starting week, and calculate
    aggregate cost per tonne-kilometre.

    Formula:
        cost_per_tonne_km = total_freight_cost_inr / total_tonne_km
        where total_tonne_km = sum(quantity_tonnes * distance_km)
              total_freight_cost_inr = sum(freight_cost_inr)

    Returns:
        pd.DataFrame sorted deterministically by (week_of, route) with columns:
        - route: Origin-Destination string
        - origin: Origin city
        - destination: Destination city
        - route_type: Short / Medium / Long
        - week_of: ISO Monday date (YYYY-MM-DD)
        - total_cost_inr: Total INR freight cost in the week
        - total_tonne_km: Total tonne-km transported in the week
        - total_quantity_tonnes: Total weight transported
        - shipment_count: Number of shipments in that route-week
        - cost_per_tonne_km: Aggregate ratio
    """
    df = df_clean.copy()

    # Assign Monday-starting week
    df["week_of"] = assign_monday_week(df["shipment_date"])

    # Group by route identity and week_of
    grouped = df.groupby(["origin", "destination", "route", "route_type", "week_of"], as_index=False).agg(
        total_cost_inr=("freight_cost_inr", "sum"),
        total_tonne_km=("tonne_km", "sum"),
        total_quantity_tonnes=("quantity_tonnes", "sum"),
        shipment_count=("shipment_id", "count")
    )

    # Division by zero safeguard
    valid_mask = grouped["total_tonne_km"] > 0
    grouped["cost_per_tonne_km"] = np.nan
    grouped.loc[valid_mask, "cost_per_tonne_km"] = (
        grouped.loc[valid_mask, "total_cost_inr"] / grouped.loc[valid_mask, "total_tonne_km"]
    )

    if (~valid_mask).any():
        logger.warning(f"Found {(~valid_mask).sum()} route-weeks with zero or negative total_tonne_km")

    # Sort deterministically by week_of, route
    grouped = grouped.sort_values(["week_of", "route"]).reset_index(drop=True)

    logger.info(
        f"Aggregated {len(df)} shipments into {len(grouped)} route-week observations "
        f"across {grouped['week_of'].nunique()} unique weeks."
    )
    return grouped
