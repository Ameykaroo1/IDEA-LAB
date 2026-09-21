"""
Multi-Criteria Ranking Tests for CRYSTAL-X.
Covers:
1. Stability scoring (lower hull energy -> higher stability score)
2. Band gap scoring (near target -> higher band gap score)
3. Dynamic weight adjustment
4. Weight renormalization when properties are NOT_AVAILABLE (does NOT assign 0)
5. Chemistry penalty on invalid candidates
"""

import pytest
from backend.services.ranking_service import MultiCriteriaRankingEngine
from backend.models.schemas import (
    PropertyPredictions,
    PropertyPrediction,
    StructuralValidationResult,
    MaterialRequirements,
    PropertyConstraint,
    RankingWeights
)


@pytest.fixture
def base_requirements():
    return MaterialRequirements(
        properties={
            "band_gap": PropertyConstraint(target=2.3, tolerance=0.3, unit="eV"),
            "energy_above_hull": PropertyConstraint(max=0.08, unit="eV/atom")
        },
        ranking_weights=RankingWeights(
            stability=0.4,
            band_gap=0.3,
            ionic_conductivity=0.2,
            chemistry=0.1
        )
    )


@pytest.fixture
def valid_validation():
    return StructuralValidationResult(status="VALID", is_valid=True)


def test_ranking_1_stability_score(base_requirements, valid_validation):
    # Candidate A: 0.01 eV/atom hull (near hull)
    preds_a = PropertyPredictions(
        energy_above_hull=PropertyPrediction(value=0.01, unit="eV/atom", source="ML"),
        band_gap=PropertyPrediction(value=2.3, unit="eV", source="ML"),
        ionic_conductivity=PropertyPrediction(value=None, unit="S/cm", source="NOT_AVAILABLE")
    )
    score_a = MultiCriteriaRankingEngine.calculate_score(preds_a, valid_validation, base_requirements)

    # Candidate B: 0.12 eV/atom hull (further from hull)
    preds_b = PropertyPredictions(
        energy_above_hull=PropertyPrediction(value=0.12, unit="eV/atom", source="ML"),
        band_gap=PropertyPrediction(value=2.3, unit="eV", source="ML"),
        ionic_conductivity=PropertyPrediction(value=None, unit="S/cm", source="NOT_AVAILABLE")
    )
    score_b = MultiCriteriaRankingEngine.calculate_score(preds_b, valid_validation, base_requirements)

    assert score_a.stability_score > score_b.stability_score
    assert score_a.total_score > score_b.total_score


def test_ranking_2_band_gap_score(base_requirements, valid_validation):
    # Candidate A: 2.31 eV (exact target match 2.3 eV)
    preds_a = PropertyPredictions(
        energy_above_hull=PropertyPrediction(value=0.02, unit="eV/atom", source="ML"),
        band_gap=PropertyPrediction(value=2.31, unit="eV", source="ML"),
        ionic_conductivity=PropertyPrediction(value=None, unit="S/cm", source="NOT_AVAILABLE")
    )
    score_a = MultiCriteriaRankingEngine.calculate_score(preds_a, valid_validation, base_requirements)

    # Candidate B: 3.5 eV (far from target 2.3 eV)
    preds_b = PropertyPredictions(
        energy_above_hull=PropertyPrediction(value=0.02, unit="eV/atom", source="ML"),
        band_gap=PropertyPrediction(value=3.5, unit="eV", source="ML"),
        ionic_conductivity=PropertyPrediction(value=None, unit="S/cm", source="NOT_AVAILABLE")
    )
    score_b = MultiCriteriaRankingEngine.calculate_score(preds_b, valid_validation, base_requirements)

    assert score_a.band_gap_score > score_b.band_gap_score
    assert score_a.total_score > score_b.total_score


def test_ranking_3_weight_adjustment(base_requirements, valid_validation):
    # Good stability, poor band gap match
    preds = PropertyPredictions(
        energy_above_hull=PropertyPrediction(value=0.00, unit="eV/atom", source="ML"),  # 100 stability
        band_gap=PropertyPrediction(value=4.0, unit="eV", source="ML"),                # low bg match
        ionic_conductivity=PropertyPrediction(value=None, unit="S/cm", source="NOT_AVAILABLE")
    )

    # High stability weight
    w_stability = RankingWeights(stability=0.8, band_gap=0.1, ionic_conductivity=0.0, chemistry=0.1)
    score_stab = MultiCriteriaRankingEngine.calculate_score(preds, valid_validation, base_requirements, weights=w_stability)

    # High band gap weight
    w_bandgap = RankingWeights(stability=0.1, band_gap=0.8, ionic_conductivity=0.0, chemistry=0.1)
    score_bg = MultiCriteriaRankingEngine.calculate_score(preds, valid_validation, base_requirements, weights=w_bandgap)

    assert score_stab.total_score > score_bg.total_score


def test_ranking_4_renormalization_for_unavailable_property(base_requirements, valid_validation):
    """
    CRITICAL REQUIREMENT:
    If ionic conductivity is NOT_AVAILABLE, do NOT assign 0.
    Weights must be renormalized across available properties.
    """
    preds = PropertyPredictions(
        energy_above_hull=PropertyPrediction(value=0.00, unit="eV/atom", source="ML"),  # 100
        band_gap=PropertyPrediction(value=2.30, unit="eV", source="ML"),                # 100
        ionic_conductivity=PropertyPrediction(value=None, unit="S/cm", source="NOT_AVAILABLE")  # None!
    )
    score = MultiCriteriaRankingEngine.calculate_score(preds, valid_validation, base_requirements)

    assert score.conductivity_score is None
    # Stability = 100, Band Gap = 100, Chemistry = 100
    # Because all available properties are 100, total score should be 100.0, NOT reduced by an unassigned 0!
    assert score.total_score == 100.0
    assert "renormalized" in score.ranking_notes[0].lower()


def test_ranking_5_invalid_chemistry_penalty(base_requirements):
    preds = PropertyPredictions(
        energy_above_hull=PropertyPrediction(value=0.01, unit="eV/atom", source="ML"),
        band_gap=PropertyPrediction(value=2.30, unit="eV", source="ML"),
        ionic_conductivity=PropertyPrediction(value=None, unit="S/cm", source="NOT_AVAILABLE")
    )

    valid_val = StructuralValidationResult(status="VALID", is_valid=True)
    invalid_val = StructuralValidationResult(status="INVALID", is_valid=False, reasons=["Missing required Si"])

    score_valid = MultiCriteriaRankingEngine.calculate_score(preds, valid_val, base_requirements)
    score_invalid = MultiCriteriaRankingEngine.calculate_score(preds, invalid_val, base_requirements)

    assert score_valid.chemistry_score > score_invalid.chemistry_score
    assert score_valid.total_score > score_invalid.total_score
