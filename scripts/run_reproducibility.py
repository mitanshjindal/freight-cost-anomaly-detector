"""Script to execute the 3-run reproducibility test and generate output/reproducibility_report.md.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.reproducibility import ReproducibilityHarness

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_reproducibility")


def main():
    logger.info("Executing 3-run reproducibility harness...")
    harness = ReproducibilityHarness()
    results = harness.execute_three_runs()

    print("\n" + "=" * 60)
    print("REPRODUCIBILITY CHECK SUMMARY")
    print("=" * 60)
    for idx, (path, sha) in enumerate(zip(results["run_files"], results["sha256_hashes"]), start=1):
        print(f"Run {idx}: {Path(path).name} -> SHA-256: {sha}")
    print(f"Byte-identical:        {results['byte_identical']}")
    print(f"DataFrames-identical:  {results['dataframes_identical']}")
    print("Report written to:     output/reproducibility_report.md")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
