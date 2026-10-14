"""Unit tests for historical and peer baseline calculations.
"""

import pandas as pd
import numpy as np
import pytest

from src.baselines import compute_baselines


def test_trailing_eight_week_history_and_no_lookahead():
    """Verify that history baseline uses up to 8 prior observations strictly before current week.
    Current week and future weeks must never contribute.
    """
    # Create 10 consecutive weeks for Route A with known costs:
    # Weeks 1 to 10 have cost = 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 100.0
    weeks = [f"2024-01-{i*7+1:02d}" for i in range(10)]  # roughly spaced
    data = []
    for i, w in enumerate(weeks):
        data.append({
            "route": "Route-A",
            "origin": "CityA",
            "destination": "CityB",
            "route_type": "Short",
            "week_of": w,
            "cost_per_tonne_km": float(i + 1),
            "total_cost_inr": 1000.0,
            "total_tonne_km": 1000.0 / (i + 1)
        })

    df = pd.DataFrame(data)
    res = compute_baselines(df, history_window_weeks=8)

    # Week 0 (first week): no prior history -> baseline is NaN
    assert np.isnan(res.loc[0, "hist_baseline"])
    assert res.loc[0, "hist_window_count"] == 0

    # Week 1: 1 prior week (cost = 1.0)
    assert res.loc[1, "hist_baseline"] == 1.0
    assert res.loc[1, "hist_window_count"] == 1

    # Week 4: 4 prior weeks (costs 1.0, 2.0, 3.0, 4.0) -> mean = 2.5
    assert res.loc[4, "hist_baseline"] == (1.0 + 2.0 + 3.0 + 4.0) / 4.0
    assert res.loc[4, "hist_window_count"] == 4

    # Week 8 (index 8): 8 prior weeks (costs 1 to 8) -> mean = (1+2+3+4+5+6+7+8)/8 = 4.5
    assert res.loc[8, "hist_baseline"] == 4.5
    assert res.loc[8, "hist_window_count"] == 8

    # Week 9 (index 9): 9 prior weeks available, but trailing window capped at 8 (costs 2 to 9)
    # mean = (2+3+4+5+6+7+8+9)/8 = 5.5
    # Ensure cost of week 9 (10.0) is NOT included!
    assert res.loc[9, "hist_baseline"] == 5.5
    assert res.loc[9, "hist_window_count"] == 8

    # Percentage change for week 9: current = 10.0, hist_avg = 5.5 -> (10/5.5 - 1)*100 = +81.818%
    expected_pct = (10.0 / 5.5 - 1.0) * 100.0
    assert pytest.approx(res.loc[9, "vs_own_history_pct"], rel=1e-4) == expected_pct


def test_peer_baseline_excludes_current_route_and_matches_route_type():
    """Verify peer average uses same week, same route_type, and excludes current route."""
    data = [
        # Week 1 - Short routes
        {"route": "Route-S1", "route_type": "Short", "week_of": "2024-01-01", "cost_per_tonne_km": 2.0},
        {"route": "Route-S2", "route_type": "Short", "week_of": "2024-01-01", "cost_per_tonne_km": 4.0},
        {"route": "Route-S3", "route_type": "Short", "week_of": "2024-01-01", "cost_per_tonne_km": 6.0},

        # Week 1 - Long route (different route_type, must not be in Short peer average)
        {"route": "Route-L1", "route_type": "Long", "week_of": "2024-01-01", "cost_per_tonne_km": 10.0},
        {"route": "Route-L2", "route_type": "Long", "week_of": "2024-01-01", "cost_per_tonne_km": 20.0},
    ]
    df = pd.DataFrame(data)
    res = compute_baselines(df)

    # For Route-S1: peers are S2 (4.0) and S3 (6.0). S1 (2.0) and Long routes must be excluded!
    # Expected peer average = (4.0 + 6.0) / 2 = 5.0
    s1 = res[res["route"] == "Route-S1"].iloc[0]
    assert s1["peer_baseline"] == 5.0
    assert s1["peer_count"] == 2
    # vs_similar_routes: (2.0 / 5.0 - 1) * 100 = -60.0%
    assert pytest.approx(s1["vs_similar_routes_pct"], rel=1e-4) == -60.0

    # For Route-L1: peer is Route-L2 (20.0)
    l1 = res[res["route"] == "Route-L1"].iloc[0]
    assert l1["peer_baseline"] == 20.0
    assert l1["peer_count"] == 1


def test_missing_history_and_missing_peers():
    """Verify graceful handling when no history or no peers exist."""
    data = [
        # Only one route of type Special
        {"route": "Solo-Route", "route_type": "Special", "week_of": "2024-01-01", "cost_per_tonne_km": 5.0}
    ]
    df = pd.DataFrame(data)
    res = compute_baselines(df)

    row = res.iloc[0]
    # No history
    assert np.isnan(row["hist_baseline"])
    assert row["hist_window_count"] == 0
    assert np.isnan(row["vs_own_history_pct"])

    # No peers
    assert np.isnan(row["peer_baseline"])
    assert row["peer_count"] == 0
    assert np.isnan(row["vs_similar_routes_pct"])
