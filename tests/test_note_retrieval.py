"""Unit tests for context note retrieval and ranking.
"""

import pandas as pd
import pytest

from src.note_retriever import NoteRetriever
from src.data_loader import load_context_notes
from config.settings import config


@pytest.fixture
def retriever():
    notes_df = load_context_notes(config.paths.context_notes)
    return NoteRetriever(notes_df)


def test_retrieval_justified_ahmedabad_mumbai(retriever):
    """Retrieve justification for Ahmedabad-Mumbai on 2025-01-20 (matches N002)."""
    justified_note, audit, rejected = retriever.find_justification_or_closest(
        route="Ahmedabad-Mumbai",
        week_of="2025-01-20",
        is_anomaly=True
    )
    assert justified_note is not None
    assert justified_note.note_id == "N002"
    assert audit.final_justified is True
    assert rejected is None


def test_retrieval_justified_chennai_bangalore_flooding(retriever):
    """Retrieve justification for Chennai-Bangalore on 2025-02-24 (matches N001)."""
    justified_note, audit, rejected = retriever.find_justification_or_closest(
        route="Chennai-Bangalore",
        week_of="2025-02-24",
        is_anomaly=True
    )
    assert justified_note is not None
    assert justified_note.note_id == "N001"
    assert audit.final_justified is True


def test_retrieval_unexplained_with_closest_rejected_note(retriever):
    """Mumbai-Pune on 2025-09-15 has no justified note, but closest candidate is N006 (2025-09-22)."""
    justified_note, audit, rejected = retriever.find_justification_or_closest(
        route="Mumbai-Pune",
        week_of="2025-09-15",
        is_anomaly=True
    )
    assert justified_note is None
    assert audit is None
    assert rejected is not None
    assert rejected.note_id == "N006"
    assert rejected.final_justified is False


def test_retrieval_unexplained_with_no_candidate_notes(retriever):
    """Delhi-Jaipur on 2024-11-11 has no context notes within the proximity window."""
    justified_note, audit, rejected = retriever.find_justification_or_closest(
        route="Delhi-Jaipur",
        week_of="2024-11-11",
        is_anomaly=True
    )
    assert justified_note is None
    assert audit is None
    assert rejected is None
