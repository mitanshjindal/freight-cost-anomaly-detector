"""Unit tests for weekly grouping and aggregated cost-per-tonne-km calculations.
"""

import pandas as pd
import numpy as np
import pytest

from src.weekly_aggregation import assign_monday_week, aggregate_weekly_costs
from src.preprocessing import preprocess_shipments


def test_assign_monday_week():
    """Verify that every date in Monday-Sunday window maps to its Monday date."""
    dates = pd.Series([
        "2024-01-01",  # Monday
        "2024-01-02",  # Tuesday
        "2024-01-05",  # Friday
        "2024-01-07",  # Sunday
        "2024-01-08",  # Next Monday
        "2025-02-28",  # Friday
        "2025-03-02",  # Sunday
    ])
    expected = [
        "2024-01-01",
        "2024-01-01",
        "2024-01-01",
        "2024-01-01",
        "2024-01-08",
        "2025-02-24",
        "2025-02-24",
    ]
    actual = assign_monday_week(dates).tolist()
    assert actual == expected


def test_aggregate_ratio_not_average_of_ratios():
    """Prove that cost_per_tonne_km uses the aggregate ratio, not the unweighted average of ratios.

    Example:
    Shipment 1: 10 tonnes, 100 km -> 1,000 t-km, cost = 5,000 INR (ratio = 5.0)
    Shipment 2: 20 tonnes, 100 km -> 2,000 t-km, cost = 8,000 INR (ratio = 4.0)

    Unweighted mean of ratios = (5.0 + 4.0) / 2 = 4.5
    Aggregate ratio = (5000 + 8000) / (1000 + 2000) = 13000 / 3000 = 4.3333...
    """
    sample_df = pd.DataFrame([
        {
            "shipment_id": "S1",
            "origin": "Mumbai",
            "destination": "Pune",
            "route_type": "Short",
            "material": "Cement",
            "quantity_tonnes": 10.0,
            "distance_km": 100.0,
            "freight_cost_inr": 5000.0,
            "shipment_date": "2024-01-03",
            "transporter": "Carrier A"
        },
        {
            "shipment_id": "S2",
            "origin": "Mumbai",
            "destination": "Pune",
            "route_type": "Short",
            "material": "Cement",
            "quantity_tonnes": 20.0,
            "distance_km": 100.0,
            "freight_cost_inr": 8000.0,
            "shipment_date": "2024-01-05",
            "transporter": "Carrier B"
        }
    ])

    clean_df, _ = preprocess_shipments(sample_df)
    weekly = aggregate_weekly_costs(clean_df)

    assert len(weekly) == 1
    row = weekly.iloc[0]
    expected_aggregate = 13000.0 / 3000.0  # 4.333333333333333
    unweighted_mean = 4.5

    assert pytest.approx(row["cost_per_tonne_km"], rel=1e-5) == expected_aggregate
    assert row["cost_per_tonne_km"] != unweighted_mean
    assert row["total_cost_inr"] == 13000.0
    assert row["total_tonne_km"] == 3000.0
    assert row["shipment_count"] == 2


def test_do_not_merge_opposite_direction_routes():
    """Verify Mumbai-Delhi and Delhi-Mumbai are treated as distinct routes."""
    sample_df = pd.DataFrame([
        {
            "shipment_id": "S1",
            "origin": "Mumbai",
            "destination": "Delhi",
            "route_type": "Long",
            "material": "Steel",
            "quantity_tonnes": 15.0,
            "distance_km": 1400.0,
            "freight_cost_inr": 42000.0,
            "shipment_date": "2024-01-03",
            "transporter": "Carrier A"
        },
        {
            "shipment_id": "S2",
            "origin": "Delhi",
            "destination": "Mumbai",
            "route_type": "Long",
            "material": "Textiles",
            "quantity_tonnes": 15.0,
            "distance_km": 1400.0,
            "freight_cost_inr": 45000.0,
            "shipment_date": "2024-01-04",
            "transporter": "Carrier B"
        }
    ])

    clean_df, _ = preprocess_shipments(sample_df)
    weekly = aggregate_weekly_costs(clean_df)

    assert len(weekly) == 2
    routes = set(weekly["route"].tolist())
    assert routes == {"Mumbai-Delhi", "Delhi-Mumbai"}
