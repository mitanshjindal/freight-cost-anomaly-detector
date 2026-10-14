"""Script to execute the evaluation harness and generate output/evaluation_report.md.
"""

import logging
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation import EvaluationHarness
from src.pipeline import ShippingCostPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_evaluation")


def main():
    logger.info("Executing evaluation harness...")
    # Load pipeline output or run pipeline
    output_csv = PROJECT_ROOT / "output" / "shipping_cost_analysis.csv"
    if not output_csv.exists():
        pipeline = ShippingCostPipeline()
        pipeline_output_df, _ = pipeline.run()
    else:
        pipeline_output_df = pd.read_csv(output_csv)

    harness = EvaluationHarness()
    summary = harness.evaluate_pipeline(pipeline_output_df)

    print("\n" + "=" * 60)
    print("EVALUATION HARNESS PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total Benchmark Cases:        {summary['total_cases']}")
    print(f"Passed Benchmark Cases:       {summary['passed_cases']} / {summary['total_cases']}")
    print(f"Overall Accuracy:             {summary['accuracy'] * 100:.1f}%")
    print(f"Anomaly Detection Precision:  {summary['anomaly_metrics']['precision'] * 100:.1f}%")
    print(f"Anomaly Detection Recall:     {summary['anomaly_metrics']['recall'] * 100:.1f}%")
    print(f"Anomaly Detection F1:         {summary['anomaly_metrics']['f1'] * 100:.1f}%")
    print(f"Justification Precision:      {summary['justification_metrics']['precision'] * 100:.1f}%")
    print(f"Justification Recall:         {summary['justification_metrics']['recall'] * 100:.1f}%")
    print(f"Justification F1:             {summary['justification_metrics']['f1'] * 100:.1f}%")
    print("Report written to:            output/evaluation_report.md")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
