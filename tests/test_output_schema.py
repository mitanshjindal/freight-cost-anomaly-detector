"""Unit tests for output CSV schema validation contract.
"""

import pandas as pd
import pytest

from src.output_writer import (
    validate_output_schema,
    format_output_dataframe,
    EXACT_OUTPUT_COLUMNS
)


def test_valid_schema_passes():
    """Verify that a compliant DataFrame passes validation."""
    data = [
        {
            "route": "Delhi-Jaipur",
            "week_of": "2024-11-11",
            "cost_per_tonne_km": "4.17",
            "vs_own_history": "+35.5% vs this route's past average",
            "vs_similar_routes": "+21.0% vs similar-length routes this week",
            "flagged": "Yes",
            "matched_note_id": "",
            "reason": "No matching note found for this route or date range."
        },
        {
            "route": "Ahmedabad-Mumbai",
            "week_of": "2025-01-20",
            "cost_per_tonne_km": "3.29",
            "vs_own_history": "+29.5% vs this route's past average",
            "vs_similar_routes": "+22.5% vs similar-length routes this week",
            "flagged": "No (justified)",
            "matched_note_id": "N002",
            "reason": "Matches note N002 dated 2025-01-20."
        }
    ]
    df = pd.DataFrame(data, columns=EXACT_OUTPUT_COLUMNS)
    is_valid, errors = validate_output_schema(df)
    assert is_valid is True
    assert len(errors) == 0


def test_wrong_column_order_fails():
    """Verify that scrambled column order is caught."""
    data = [
        {
            "week_of": "2024-11-11",  # out of order
            "route": "Delhi-Jaipur",
            "cost_per_tonne_km": "4.17",
            "vs_own_history": "+35.5% vs this route's past average",
            "vs_similar_routes": "+21.0% vs similar-length routes this week",
            "flagged": "Yes",
            "matched_note_id": "",
            "reason": "Reason"
        }
    ]
    df = pd.DataFrame(data)
    is_valid, errors = validate_output_schema(df)
    assert is_valid is False
    assert any("Column mismatch" in e for e in errors)


def test_inconsistent_matched_note_id_fails():
    """flagged == 'No (justified)' MUST have a matched_note_id.
    flagged == 'Yes' or 'No' MUST NOT have a matched_note_id.
    """
    # Case A: Justified without note ID
    df_missing_id = pd.DataFrame([{
        "route": "Ahmedabad-Mumbai",
        "week_of": "2025-01-20",
        "cost_per_tonne_km": "3.29",
        "vs_own_history": "+29.5% vs this route's past average",
        "vs_similar_routes": "+22.5% vs similar-length routes this week",
        "flagged": "No (justified)",
        "matched_note_id": "",  # Missing!
        "reason": "Some reason"
    }], columns=EXACT_OUTPUT_COLUMNS)
    is_valid, errors = validate_output_schema(df_missing_id)
    assert is_valid is False
    assert any("matched_note_id is empty" in e for e in errors)

    # Case B: Unexplained with note ID
    df_spurious_id = pd.DataFrame([{
        "route": "Delhi-Jaipur",
        "week_of": "2024-11-11",
        "cost_per_tonne_km": "4.17",
        "vs_own_history": "+35.5% vs this route's past average",
        "vs_similar_routes": "+21.0% vs similar-length routes this week",
        "flagged": "Yes",
        "matched_note_id": "N001",  # Should be empty!
        "reason": "Some reason"
    }], columns=EXACT_OUTPUT_COLUMNS)
    is_valid, errors = validate_output_schema(df_spurious_id)
    assert is_valid is False
    assert any("should be blank" in e for e in errors)
