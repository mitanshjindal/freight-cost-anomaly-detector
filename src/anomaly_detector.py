"""Transparent, deterministic anomaly detection module for freight costs.
"""

from enum import Enum
import logging
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

from config.settings import AnomalyThresholds

logger = logging.getLogger(__name__)


class AnomalyState(str, Enum):
    """Internal anomaly operational states."""
    NO_ANOMALY = "NO_ANOMALY"
    ANOMALY_JUSTIFIED = "ANOMALY_JUSTIFIED"
    ANOMALY_UNEXPLAINED = "ANOMALY_UNEXPLAINED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AnomalyDetector:
    """Deterministic anomaly detector for route-week freight costs."""

    def __init__(self, thresholds: Optional[AnomalyThresholds] = None):
        self.thresholds = thresholds or AnomalyThresholds()

    def evaluate_observation(
        self,
        cost_per_tonne_km: float,
        vs_own_history_pct: Optional[float],
        vs_similar_routes_pct: Optional[float],
        hist_window_count: int,
        peer_count: int
    ) -> Dict[str, Any]:
        """Evaluate a single route-week for numerical cost anomalies.

        Evaluation Rules:
        1. If no prior historical baseline exists (hist_window_count == 0),
           we cannot determine if costs are rising. Mark INSUFFICIENT_DATA.
        2. History spike:
           vs_own_history_pct >= thresholds.history_spike_threshold_pct (default: 15.0%).
        3. Peer spike:
           Cost must be rising vs history (vs_own_history_pct >= min_rise_for_peer_anomaly_pct, default 5.0%)
           AND significantly higher than peer routes (vs_similar_routes_pct >= peer_spike_threshold_pct, default 20.0%).
           This strictly honors:
           - "Costs are rising"
           - "Do not confuse a positive peer difference with proof that costs have recently increased"
        4. A numerical anomaly is flagged if either (2) or (3) is true.

        Returns:
            Dict containing:
            - is_anomaly (bool)
            - detection_type (str): "DUAL_SPIKE", "HISTORY_SPIKE", "PEER_OUTLIER", "NONE", "INSUFFICIENT_HISTORY"
            - detection_reasons (List[str])
            - has_sufficient_history (bool)
        """
        # Rule 1: Missing historical baseline
        if hist_window_count == 0 or vs_own_history_pct is None or np.isnan(vs_own_history_pct):
            return {
                "is_anomaly": False,
                "detection_type": "INSUFFICIENT_HISTORY",
                "detection_reasons": ["Insufficient historical observations to establish a baseline trend."],
                "has_sufficient_history": False
            }

        reasons = []
        is_history_spike = vs_own_history_pct >= self.thresholds.history_spike_threshold_pct

        is_peer_spike = False
        if vs_similar_routes_pct is not None and not np.isnan(vs_similar_routes_pct):
            # Cost must be rising AND significantly higher than peers
            is_rising = vs_own_history_pct >= self.thresholds.min_rise_for_peer_anomaly_pct
            if is_rising and (vs_similar_routes_pct >= self.thresholds.peer_spike_threshold_pct):
                is_peer_spike = True

        if is_history_spike:
            reasons.append(
                f"History spike: {vs_own_history_pct:+.1f}% vs past 8-week average "
                f"(threshold: +{self.thresholds.history_spike_threshold_pct:.1f}%)"
            )

        if is_peer_spike:
            reasons.append(
                f"Peer outlier: {vs_similar_routes_pct:+.1f}% vs similar routes "
                f"(threshold: +{self.thresholds.peer_spike_threshold_pct:.1f}%) with confirmed cost rise ({vs_own_history_pct:+.1f}%)"
            )

        is_anomaly = is_history_spike or is_peer_spike
        if is_history_spike and is_peer_spike:
            detection_type = "DUAL_SPIKE"
        elif is_history_spike:
            detection_type = "HISTORY_SPIKE"
        elif is_peer_spike:
            detection_type = "PEER_OUTLIER"
        else:
            detection_type = "NONE"

        return {
            "is_anomaly": is_anomaly,
            "detection_type": detection_type,
            "detection_reasons": reasons,
            "has_sufficient_history": True
        }

    def detect_anomalies(self, df_baselines: pd.DataFrame) -> pd.DataFrame:
        """Run numerical anomaly detection over the complete dataset of route-weeks.

        Returns:
            pd.DataFrame with added columns:
            - is_numerical_anomaly (bool)
            - detection_type (str)
            - detection_reasons (list of str)
            - has_sufficient_history (bool)
        """
        df = df_baselines.copy()
        is_anomaly_col = []
        detection_type_col = []
        detection_reasons_col = []
        has_suff_hist_col = []

        for _, row in df.iterrows():
            eval_res = self.evaluate_observation(
                cost_per_tonne_km=row["cost_per_tonne_km"],
                vs_own_history_pct=row["vs_own_history_pct"],
                vs_similar_routes_pct=row["vs_similar_routes_pct"],
                hist_window_count=int(row["hist_window_count"]),
                peer_count=int(row["peer_count"])
            )
            is_anomaly_col.append(eval_res["is_anomaly"])
            detection_type_col.append(eval_res["detection_type"])
            detection_reasons_col.append(eval_res["detection_reasons"])
            has_suff_hist_col.append(eval_res["has_sufficient_history"])

        df["is_numerical_anomaly"] = is_anomaly_col
        df["detection_type"] = detection_type_col
        df["detection_reasons"] = detection_reasons_col
        df["has_sufficient_history"] = has_suff_hist_col

        num_anomalies = df["is_numerical_anomaly"].sum()
        logger.info(f"Anomaly detection complete: {num_anomalies} anomalies detected out of {len(df)} route-weeks.")
        return df
