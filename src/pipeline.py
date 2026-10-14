"""End-to-end pipeline orchestrator for the FreightTiger Freight Cost Analytics Platform.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pandas as pd

from config.settings import AppConfig, config
from src.data_loader import load_shipments, load_context_notes
from src.preprocessing import preprocess_shipments
from src.weekly_aggregation import aggregate_weekly_costs
from src.baselines import compute_baselines
from src.anomaly_detector import AnomalyDetector
from src.note_retriever import NoteRetriever
from src.explanation_generator import ExplanationGenerator
from src.output_writer import format_output_dataframe, validate_output_schema, write_output_csv

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Summary metrics of a complete pipeline execution."""
    raw_shipments_count: int
    routes_count: int
    weeks_count: int
    route_weeks_count: int
    anomalies_detected: int
    justified_anomalies: int
    unexplained_anomalies: int
    output_rows_count: int
    output_csv_path: str


class ShippingCostPipeline:
    """Orchestrates data loading, aggregation, baseline estimation, anomaly detection,
    RAG evidence validation, explanation generation, and output formatting.
    """

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.config = cfg or config
        self.anomaly_detector = AnomalyDetector(self.config.thresholds)
        self.explanation_generator = ExplanationGenerator(self.config.llm)

    def run(
        self,
        shipments_path: Optional[Path] = None,
        notes_path: Optional[Path] = None,
        output_path: Optional[Path] = None
    ) -> Tuple[pd.DataFrame, PipelineMetrics]:
        """Execute the full end-to-end shipping cost analysis.

        Returns:
            Tuple[pd.DataFrame, PipelineMetrics]: Formatted output DataFrame and summary metrics.
        """
        s_path = shipments_path or self.config.paths.shipment_records
        n_path = notes_path or self.config.paths.context_notes
        out_path = output_path or self.config.paths.final_output

        # 1. Load data
        raw_shipments = load_shipments(s_path)
        notes_df = load_context_notes(n_path)

        # 2. Preprocess
        clean_shipments, audit_report = preprocess_shipments(raw_shipments)

        # 3. Weekly aggregation
        df_weekly = aggregate_weekly_costs(clean_shipments)

        # 4. Compute baselines
        df_baselines = compute_baselines(
            df_weekly,
            history_window_weeks=self.config.baselines.history_window_weeks,
            min_history_observations=self.config.baselines.min_history_observations
        )

        # 5. Detect anomalies
        df_anomalies = self.anomaly_detector.detect_anomalies(df_baselines)

        # 6. Retrieve notes & validate evidence
        retriever = NoteRetriever(notes_df)

        matched_note_ids = []
        reasons = []

        for _, row in df_anomalies.iterrows():
            r = row["route"]
            w = row["week_of"]
            c = row["cost_per_tonne_km"]
            is_anom = row["is_numerical_anomaly"]
            has_hist = row["has_sufficient_history"]
            vs_hist = row["vs_own_history_pct"]
            vs_peer = row["vs_similar_routes_pct"]

            if is_anom:
                matched_note, justified_audit, rejected_audit = retriever.find_justification_or_closest(
                    route=r,
                    week_of=w,
                    is_anomaly=True
                )
                matched_id = matched_note.note_id if matched_note else ""
                reason = self.explanation_generator.generate_explanation(
                    route=r,
                    week_of=w,
                    cost_per_tonne_km=c,
                    vs_own_history_pct=vs_hist,
                    vs_similar_routes_pct=vs_peer,
                    is_anomaly=True,
                    has_sufficient_history=has_hist,
                    matched_note=matched_note,
                    closest_rejected_audit=rejected_audit
                )
            else:
                matched_id = ""
                reason = self.explanation_generator.generate_explanation(
                    route=r,
                    week_of=w,
                    cost_per_tonne_km=c,
                    vs_own_history_pct=vs_hist,
                    vs_similar_routes_pct=vs_peer,
                    is_anomaly=False,
                    has_sufficient_history=has_hist
                )

            matched_note_ids.append(matched_id)
            reasons.append(reason)

        df_anomalies["matched_note_id"] = matched_note_ids
        df_anomalies["reason"] = reasons

        # 7. Format output DataFrame according to contract
        formatted_df = format_output_dataframe(df_anomalies)

        # 8. Write to CSV
        resolved_csv_path = write_output_csv(formatted_df, out_path)

        # 9. Compute metrics
        anomalies_count = int(df_anomalies["is_numerical_anomaly"].sum())
        justified_count = sum(1 for nid in matched_note_ids if bool(nid))
        unexplained_count = anomalies_count - justified_count

        metrics = PipelineMetrics(
            raw_shipments_count=len(raw_shipments),
            routes_count=int(df_weekly["route"].nunique()),
            weeks_count=int(df_weekly["week_of"].nunique()),
            route_weeks_count=len(df_weekly),
            anomalies_detected=anomalies_count,
            justified_anomalies=justified_count,
            unexplained_anomalies=unexplained_count,
            output_rows_count=len(formatted_df),
            output_csv_path=str(resolved_csv_path)
        )

        logger.info(f"Pipeline run complete: {metrics}")
        return formatted_df, metrics
