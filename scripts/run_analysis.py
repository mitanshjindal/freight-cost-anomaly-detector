"""Script to execute the complete FreightTiger shipping cost analysis.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import ShippingCostPipeline
from config.settings import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_analysis")


def main():
    logger.info("Starting Shipping Cost Analysis Pipeline...")
    pipeline = ShippingCostPipeline(config)
    df, metrics = pipeline.run()

    print("\n" + "=" * 60)
    print("FREIGHT TIGER SHIPPING COST ANALYSIS — EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Raw shipments processed:       {metrics.raw_shipments_count:,}")
    print(f"Routes evaluated:              {metrics.routes_count}")
    print(f"Weeks evaluated:               {metrics.weeks_count}")
    print(f"Total route-weeks:             {metrics.route_weeks_count}")
    print(f"Anomalies detected:            {metrics.anomalies_detected}")
    print(f"  - Justified anomalies:       {metrics.justified_anomalies}")
    print(f"  - Unexplained anomalies:     {metrics.unexplained_anomalies}")
    print(f"Output CSV generated:          {metrics.output_rows_count} rows")
    print(f"Saved to:                      {metrics.output_csv_path}")
    print("=" * 60 + "\n")

    # Display sample rows
    print("Sample output rows:")
    print(df.head(10).to_string())
    print("\nSample flagged rows:")
    flagged = df[df["flagged"] != "No"]
    print(flagged.to_string())


if __name__ == "__main__":
    main()
