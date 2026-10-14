"""Historical and peer baseline calculations matching case study specifications.
"""

import logging
from typing import Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_baselines(
    df_weekly: pd.DataFrame,
    history_window_weeks: int = 8,
    min_history_observations: int = 1
) -> pd.DataFrame:
    """Calculate trailing historical and same-week peer baselines for each route-week.

    Guarantees:
    1. Own history:
       - Uses strictly weeks prior to the current week (week_of < current_week_of).
       - Rolling trailing up to `history_window_weeks` (default 8).
       - Never includes current week (no self-reference).
       - Never includes future weeks (no look-ahead).
       - Does not pad with zeros or interpolate missing weeks.
       - Records count of historical observations used (`hist_window_count`).
    2. Similar routes (peer baseline):
       - Uses the same week_of.
       - Compares routes with the exact same route_type (Short, Medium, Long).
       - Strictly excludes the current route from its peer average.
       - Calculates the unweighted average of peer route-week cost_per_tonne_km.
       - Records peer count (`peer_count`).

    Returns:
        pd.DataFrame with added columns:
        - hist_baseline: Trailing 8-week average cost per tonne-km (float or None)
        - hist_window_count: Number of prior weeks contributing to baseline (int)
        - vs_own_history_pct: Percentage change vs own history (float or None)
        - peer_baseline: Average cost per tonne-km of peer routes in same week (float or None)
        - peer_count: Number of peer routes contributing to baseline (int)
        - vs_similar_routes_pct: Percentage change vs peer baseline (float or None)
    """
    df = df_weekly.copy()

    # Pre-sort to guarantee chronological order per route
    df = df.sort_values(["route", "week_of"]).reset_index(drop=True)

    n_rows = len(df)
    hist_baseline = [np.nan] * n_rows
    hist_window_count = [0] * n_rows
    vs_own_history_pct = [np.nan] * n_rows

    peer_baseline = [np.nan] * n_rows
    peer_count = [0] * n_rows
    vs_similar_routes_pct = [np.nan] * n_rows

    # Group by route for historical calculation
    route_groups = {route: group for route, group in df.groupby("route")}

    # Group by (week_of, route_type) for peer calculation
    peer_groups = {(w, rt): group for (w, rt), group in df.groupby(["week_of", "route_type"])}

    for i in range(n_rows):
        row = df.iloc[i]
        curr_route = row["route"]
        curr_week = row["week_of"]
        curr_cost = row["cost_per_tonne_km"]
        curr_route_type = row["route_type"]

        # --- 1. Own History Baseline ---
        route_df = route_groups[curr_route]
        # Strictly prior observations
        prior_obs = route_df[route_df["week_of"] < curr_week].sort_values("week_of")
        if len(prior_obs) >= min_history_observations:
            # Trailing window up to 8
            trailing_window = prior_obs.tail(history_window_weeks)
            h_count = len(trailing_window)
            h_avg = trailing_window["cost_per_tonne_km"].mean()

            hist_baseline[i] = h_avg
            hist_window_count[i] = h_count
            if pd.notnull(curr_cost) and pd.notnull(h_avg) and h_avg > 0:
                vs_own_history_pct[i] = (curr_cost / h_avg - 1.0) * 100.0

        # --- 2. Peer Route Baseline ---
        peers_df = peer_groups.get((curr_week, curr_route_type))
        if peers_df is not None:
            # Exclude current route
            other_peers = peers_df[peers_df["route"] != curr_route]
            p_count = len(other_peers)
            if p_count > 0:
                p_avg = other_peers["cost_per_tonne_km"].mean()
                peer_baseline[i] = p_avg
                peer_count[i] = p_count
                if pd.notnull(curr_cost) and pd.notnull(p_avg) and p_avg > 0:
                    vs_similar_routes_pct[i] = (curr_cost / p_avg - 1.0) * 100.0

    df["hist_baseline"] = hist_baseline
    df["hist_window_count"] = hist_window_count
    df["vs_own_history_pct"] = vs_own_history_pct

    df["peer_baseline"] = peer_baseline
    df["peer_count"] = peer_count
    df["vs_similar_routes_pct"] = vs_similar_routes_pct

    # Sort deterministically by week_of, route
    df = df.sort_values(["week_of", "route"]).reset_index(drop=True)

    logger.info("Successfully computed historical and peer baselines.")
    return df
