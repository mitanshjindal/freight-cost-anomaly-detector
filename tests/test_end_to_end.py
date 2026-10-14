"""End-to-end integration test on a synthetic dataset with known ground truth.
"""

from pathlib import Path
import pandas as pd
import pytest

from src.pipeline import ShippingCostPipeline
from config.settings import AppConfig, ProjectPaths, AnomalyThresholds, BaselineSettings


def test_end_to_end_synthetic_pipeline(tmp_path):
    """Run full pipeline on a compact synthetic dataset with known expected outputs."""
    # 1. Create synthetic shipments
    # 2 routes of route_type 'Short':
    # Route A (CityA-CityB) has 4 prior weeks with cost 2.0, then week 5 spikes to 3.5 (+75% spike, justified by note)
    # Route B (CityC-CityD) has 4 prior weeks with cost 2.0, then week 5 spikes to 3.0 (+50% spike, unexplained)
    weeks = ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22", "2024-01-29"]

    records = []
    shp_id = 1
    for w in weeks:
        cost_a = 3500.0 if w == "2024-01-29" else 2000.0
        records.append({
            "shipment_id": f"SHP{shp_id:04d}",
            "origin": "CityA",
            "destination": "CityB",
            "route_type": "Short",
            "material": "Cement",
            "quantity_tonnes": 10.0,
            "distance_km": 100.0,  # 1000 tonne-km
            "freight_cost_inr": cost_a,
            "shipment_date": w,
            "transporter": "TestCarrier"
        })
        shp_id += 1

        cost_b = 3000.0 if w == "2024-01-29" else 2000.0
        records.append({
            "shipment_id": f"SHP{shp_id:04d}",
            "origin": "CityC",
            "destination": "CityD",
            "route_type": "Short",
            "material": "Cement",
            "quantity_tonnes": 10.0,
            "distance_km": 100.0,
            "freight_cost_inr": cost_b,
            "shipment_date": w,
            "transporter": "TestCarrier"
        })
        shp_id += 1

    shipments_csv = tmp_path / "test_shipments.csv"
    pd.DataFrame(records).to_csv(shipments_csv, index=False)

    # 2. Create synthetic context notes
    # Note justifies CityA-CityB on 2024-01-29
    notes = [
        {
            "note_id": "SYNTH_01",
            "date": "2024-01-29",
            "applies_to": "CityA-CityB",
            "note": "Bridge repair surcharge on CityA-CityB forced higher detour cost."
        }
    ]
    notes_csv = tmp_path / "test_notes.csv"
    pd.DataFrame(notes).to_csv(notes_csv, index=False)

    output_csv = tmp_path / "test_output.csv"

    # 3. Configure custom pipeline
    custom_cfg = AppConfig(
        paths=ProjectPaths(
            shipment_records=shipments_csv,
            context_notes=notes_csv,
            final_output=output_csv
        ),
        baselines=BaselineSettings(history_window_weeks=4),
        thresholds=AnomalyThresholds(history_spike_threshold_pct=25.0, peer_spike_threshold_pct=20.0)
    )

    # Inject note SYNTH_01 knowledge into validator for this synthetic test
    from src.evidence_validator import EvidenceValidator
    EvidenceValidator.KNOWLEDGE_BASE["SYNTH_01"] = {
        "effective_start": "2024-01-29",
        "effective_end": "2024-02-04",
        "supports_cost_increase": True,
        "summary": "bridge repair surcharge forced higher detour cost",
        "disqualification_reason": None
    }

    pipeline = ShippingCostPipeline(custom_cfg)
    df_out, metrics = pipeline.run(
        shipments_path=shipments_csv,
        notes_path=notes_csv,
        output_path=output_csv
    )

    # 4. Verify outputs
    assert len(df_out) == 10  # 2 routes * 5 weeks
    assert output_csv.exists()

    # Route A week 5: should be flagged as No (justified) with SYNTH_01
    row_a_w5 = df_out[(df_out["route"] == "CityA-CityB") & (df_out["week_of"] == "2024-01-29")].iloc[0]
    assert row_a_w5["cost_per_tonne_km"] == "3.50"
    assert row_a_w5["flagged"] == "No (justified)"
    assert row_a_w5["matched_note_id"] == "SYNTH_01"
    assert "Matches note SYNTH_01" in row_a_w5["reason"]

    # Route B week 5: should be flagged as Yes (unexplained) with empty note ID
    row_b_w5 = df_out[(df_out["route"] == "CityC-CityD") & (df_out["week_of"] == "2024-01-29")].iloc[0]
    assert row_b_w5["cost_per_tonne_km"] == "3.00"
    assert row_b_w5["flagged"] == "Yes"
    assert row_b_w5["matched_note_id"] == ""
    assert "No matching note found" in row_b_w5["reason"]

    # Non-anomalous row (week 2)
    row_a_w2 = df_out[(df_out["route"] == "CityA-CityB") & (df_out["week_of"] == "2024-01-08")].iloc[0]
    assert row_a_w2["flagged"] == "No"
    assert row_a_w2["matched_note_id"] == ""
