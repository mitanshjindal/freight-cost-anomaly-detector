"""Unit tests for evidence validation rules (N001 to N010 guardrails).
"""

import pytest
from src.evidence_validator import EvidenceValidator


@pytest.fixture
def validator():
    return EvidenceValidator()


def test_n001_flooding_disruption_valid_inside_window(validator):
    """N001 justifies Chennai-Bangalore from Feb 24 to Mar 8, 2025."""
    # Week 1 of flooding: Feb 24, 2025
    audit1 = validator.validate_candidate(
        note_id="N001",
        route="Chennai-Bangalore",
        week_of="2025-02-24"
    )
    assert audit1.route_applicability_passed is True
    assert audit1.temporal_applicability_passed is True
    assert audit1.supports_cost_increase is True
    assert audit1.final_justified is True

    # Week 2 of flooding: Mar 03, 2025 (spans Mar 3 to Mar 9, overlaps Feb 24 - Mar 8)
    audit2 = validator.validate_candidate(
        note_id="N001",
        route="Chennai-Bangalore",
        week_of="2025-03-03"
    )
    assert audit2.final_justified is True


def test_n001_flooding_disruption_invalid_outside_window(validator):
    """N001 CANNOT justify Chennai-Bangalore on Mar 10, 2025 (flooding ended Mar 8)."""
    audit = validator.validate_candidate(
        note_id="N001",
        route="Chennai-Bangalore",
        week_of="2025-03-10"
    )
    assert audit.route_applicability_passed is True
    assert audit.temporal_applicability_passed is False
    assert audit.final_justified is False


def test_n001_invalid_on_different_route(validator):
    """N001 applies only to Chennai-Bangalore, not to Mumbai-Pune."""
    audit = validator.validate_candidate(
        note_id="N001",
        route="Mumbai-Pune",
        week_of="2025-02-24"
    )
    assert audit.route_applicability_passed is False
    assert audit.final_justified is False


def test_n002_festival_surcharge_valid(validator):
    """N002 justifies Ahmedabad-Mumbai during week of Jan 20, 2025."""
    audit = validator.validate_candidate(
        note_id="N002",
        route="Ahmedabad-Mumbai",
        week_of="2025-01-20"
    )
    assert audit.route_applicability_passed is True
    assert audit.temporal_applicability_passed is True
    assert audit.supports_cost_increase is True
    assert audit.final_justified is True


def test_n003_diesel_price_rise_all_routes(validator):
    """N003 applies nationwide starting week of May 5, 2025."""
    audit = validator.validate_candidate(
        note_id="N003",
        route="Delhi-Jaipur",
        week_of="2025-05-05"
    )
    assert audit.route_applicability_passed is True
    assert audit.temporal_applicability_passed is True
    assert audit.supports_cost_increase is True
    assert audit.final_justified is True


def test_n004_toll_plaza_outside_dataset_disqualified(validator):
    """N004 states affected routes are not part of this dataset; must NEVER justify any route."""
    for r in ["Mumbai-Delhi", "Delhi-Jaipur", "Chennai-Bangalore"]:
        audit = validator.validate_candidate(note_id="N004", route=r, week_of="2024-03-11")
        assert audit.route_applicability_passed is False
        assert audit.final_justified is False


def test_n005_costs_not_affected_disqualified(validator):
    """N005 states costs were not significantly affected; must NEVER justify a rate increase."""
    audit = validator.validate_candidate(
        note_id="N005",
        route="Mumbai-Delhi",
        week_of="2024-07-29"
    )
    assert audit.route_applicability_passed is True
    assert audit.temporal_applicability_passed is True
    assert audit.supports_cost_increase is False
    assert audit.final_justified is False


def test_n006_stable_demand_no_disruptions_disqualified(validator):
    """N006 mentions stable demand and no major disruptions; cannot justify a cost increase."""
    audit = validator.validate_candidate(
        note_id="N006",
        route="Mumbai-Pune",
        week_of="2025-09-15"
    )
    assert audit.supports_cost_increase is False
    assert audit.final_justified is False


def test_n007_improved_road_conditions_disqualified(validator):
    """N007 describes road resurfacing and improved conditions; cannot justify a cost increase."""
    audit = validator.validate_candidate(
        note_id="N007",
        route="Delhi-Jaipur",
        week_of="2024-05-20"
    )
    assert audit.supports_cost_increase is False
    assert audit.final_justified is False


def test_n008_normal_freight_movement_disqualified(validator):
    """N008 states freight movement remained normal; cannot justify a cost increase."""
    audit = validator.validate_candidate(
        note_id="N008",
        route="Kolkata-Bhubaneswar",
        week_of="2025-06-09"
    )
    assert audit.supports_cost_increase is False
    assert audit.final_justified is False


def test_n009_returned_to_normal_disqualified(validator):
    """N009 confirms Chennai-Bangalore returned to normal; cannot justify cost increases."""
    audit = validator.validate_candidate(
        note_id="N009",
        route="Chennai-Bangalore",
        week_of="2025-03-17"
    )
    assert audit.supports_cost_increase is False
    assert audit.final_justified is False


def test_n010_compliance_costs_absorbed_disqualified(validator):
    """N010 tracking mandate compliance costs were absorbed without rate change; disqualified."""
    audit = validator.validate_candidate(
        note_id="N010",
        route="Mumbai-Delhi",
        week_of="2025-10-27"
    )
    assert audit.supports_cost_increase is False
    assert audit.final_justified is False
