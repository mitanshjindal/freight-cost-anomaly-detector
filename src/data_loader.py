"""Data loading and schema validation module for FreightTiger freight analytics platform.
"""

import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_SHIPMENT_COLUMNS = [
    "shipment_id",
    "origin",
    "destination",
    "route_type",
    "material",
    "quantity_tonnes",
    "distance_km",
    "freight_cost_inr",
    "shipment_date",
    "transporter"
]

REQUIRED_NOTE_COLUMNS = [
    "note_id",
    "date",
    "applies_to",
    "note"
]


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


def load_shipments(file_path: Union[str, Path]) -> pd.DataFrame:
    """Load and validate raw shipment records CSV.

    Args:
        file_path: Path to shipment_records.csv

    Returns:
        pd.DataFrame: Clean validated DataFrame

    Raises:
        FileNotFoundError: If the file does not exist.
        DataValidationError: If required columns are missing or data contains fatal invalidities.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Shipment records file not found at: {path.resolve()}")

    logger.info(f"Loading shipment records from {path.resolve()}")
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise DataValidationError(f"Failed to parse CSV file at {path}: {str(e)}") from e

    # 1. Column presence check
    missing_cols = [c for c in REQUIRED_SHIPMENT_COLUMNS if c not in df.columns]
    if missing_cols:
        raise DataValidationError(f"Shipment records missing required columns: {missing_cols}")

    # 2. Duplicate shipment_id check
    dup_count = df["shipment_id"].duplicated().sum()
    if dup_count > 0:
        dups = df[df["shipment_id"].duplicated(keep=False)]["shipment_id"].tolist()
        logger.warning(f"Found {dup_count} duplicate shipment_ids in input data: {dups[:5]}")
        # Note: We do not silently drop unless instructed, but report it
        raise DataValidationError(f"Duplicate shipment IDs found in dataset ({dup_count} duplicates)")

    # 3. Null values check
    null_counts = df[REQUIRED_SHIPMENT_COLUMNS].isnull().sum()
    if null_counts.any():
        cols_with_nulls = null_counts[null_counts > 0].to_dict()
        raise DataValidationError(f"Unexpected null values in required shipment columns: {cols_with_nulls}")

    logger.info(f"Successfully loaded {len(df)} shipment records across {df['route_type'].nunique()} route types.")
    return df


def load_context_notes(file_path: Union[str, Path]) -> pd.DataFrame:
    """Load and validate context notes CSV.

    Args:
        file_path: Path to context_notes.csv

    Returns:
        pd.DataFrame: Clean validated DataFrame

    Raises:
        FileNotFoundError: If the file does not exist.
        DataValidationError: If required columns are missing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Context notes file not found at: {path.resolve()}")

    logger.info(f"Loading context notes from {path.resolve()}")
    df = pd.read_csv(path)

    missing_cols = [c for c in REQUIRED_NOTE_COLUMNS if c not in df.columns]
    if missing_cols:
        raise DataValidationError(f"Context notes missing required columns: {missing_cols}")

    # Validate note_id uniqueness
    if df["note_id"].duplicated().any():
        raise DataValidationError("Duplicate note_id found in context notes.")

    logger.info(f"Successfully loaded {len(df)} context notes.")
    return df
