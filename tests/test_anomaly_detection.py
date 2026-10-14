"""Unit tests for transparent deterministic anomaly detection logic.
"""

import pytest
from src.anomaly_detector import AnomalyDetector
from config.settings import AnomalyThresholds


@pytest.fixture
def detector():
    # Use default thresholds: history_spike = 15.0%, peer_spike = 20.0%, min_rise = 5.0%
    return AnomalyDetector(AnomalyThresholds(
        history_spike_threshold_pct=15.0,
        peer_spike_threshold_pct=20.0,
        min_rise_for_peer_anomaly_pct=5.0
    ))


def test_history_spike_detected(detector):
    """Severe history spike alone triggers an anomaly."""
    res = detector.evaluate_observation(
        cost_per_tonne_km=4.17,
        vs_own_history_pct=35.5,
        vs_similar_routes_pct=5.0,  # Peer not anomalous
        hist_window_count=8,
        peer_count=2
    )
    assert res["is_anomaly"] is True
    assert res["detection_type"] == "HISTORY_SPIKE"


def test_peer_spike_with_rising_cost_detected(detector):
    """Peer spike with rising cost triggers an anomaly (e.g. Mumbai-Pune 2025-09-15)."""
    res = detector.evaluate_observation(
        cost_per_tonne_km=3.98,
        vs_own_history_pct=9.2,   # Rising (> 5%)
        vs_similar_routes_pct=23.6,  # Higher than peers (> 20%)
        hist_window_count=8,
        peer_count=1
    )
    assert res["is_anomaly"] is True
    assert res["detection_type"] == "PEER_OUTLIER"


def test_high_peer_without_cost_rise_is_not_an_anomaly(detector):
    """CRITICAL RULE: Do not confuse a positive peer difference with proof that costs have recently increased.
    If cost is flat or falling vs own history (-2.0%), high peer difference alone does not make it an anomaly.
    """
    res = detector.evaluate_observation(
        cost_per_tonne_km=4.00,
        vs_own_history_pct=-2.0,   # NOT rising
        vs_similar_routes_pct=25.0,  # Peer is high
        hist_window_count=8,
        peer_count=2
    )
    assert res["is_anomaly"] is False
    assert res["detection_type"] == "NONE"


def test_dual_spike_detected(detector):
    """Both history and peer thresholds exceeded (e.g. Ahmedabad-Mumbai 2025-01-20)."""
    res = detector.evaluate_observation(
        cost_per_tonne_km=3.29,
        vs_own_history_pct=29.5,
        vs_similar_routes_pct=22.5,
        hist_window_count=8,
        peer_count=2
    )
    assert res["is_anomaly"] is True
    assert res["detection_type"] == "DUAL_SPIKE"


def test_missing_history_handled_safely(detector):
    """Initial observation with no history baseline must not be flagged."""
    res = detector.evaluate_observation(
        cost_per_tonne_km=3.00,
        vs_own_history_pct=None,
        vs_similar_routes_pct=25.0,
        hist_window_count=0,
        peer_count=1
    )
    assert res["is_anomaly"] is False
    assert res["detection_type"] == "INSUFFICIENT_HISTORY"
    assert res["has_sufficient_history"] is False


def test_configurable_thresholds():
    """Verify that custom thresholds take immediate effect."""
    custom_detector = AnomalyDetector(AnomalyThresholds(
        history_spike_threshold_pct=50.0,  # High threshold
        peer_spike_threshold_pct=50.0,
        min_rise_for_peer_anomaly_pct=10.0
    ))
    res = custom_detector.evaluate_observation(
        cost_per_tonne_km=3.29,
        vs_own_history_pct=29.5,  # < 50%
        vs_similar_routes_pct=22.5,  # < 50%
        hist_window_count=8,
        peer_count=2
    )
    assert res["is_anomaly"] is False
