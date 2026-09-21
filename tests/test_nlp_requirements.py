"""
Tests for NLP Requirement Extraction Service in CRYSTAL-X.
Covers 10 mandatory NLP extraction scenarios:
1. Silicon extraction
2. Multiple required elements (Li, Si)
3. Excluded elements (Pb, Cd, Hg)
4. Band gap target (2.3 eV)
5. Band gap range (2.0 - 3.0 eV)
6. Energy above hull (0.05 eV/atom)
7. Qualitative stability ("stable material")
8. Qualitative conductivity ("high ionic conductivity")
9. Application extraction ("battery material")
10. Excluded toxic elements ("no Pb Cd Hg")
"""

import pytest
from backend.services.nlp_requirement_service import NLPRequirementService
from backend.services.constraint_normalizer import ConstraintNormalizer


@pytest.fixture
def nlp_service():
    return NLPRequirementService()


def test_1_silicon_extraction(nlp_service):
    text = "I need a silicon-based material for energy storage"
    res = nlp_service.parse_text(text)
    assert "Si" in res["required_elements"]


def test_2_multiple_required_elements(nlp_service):
    text = "Material containing lithium and silicon for advanced anodes"
    res = nlp_service.parse_text(text)
    assert "Li" in res["required_elements"]
    assert "Si" in res["required_elements"]


def test_3_excluded_elements(nlp_service):
    text = "I need a silicon material without lead, cadmium and mercury"
    res = nlp_service.parse_text(text)
    assert "Si" in res["required_elements"]
    assert "Pb" in res["excluded_elements"]
    assert "Cd" in res["excluded_elements"]
    assert "Hg" in res["excluded_elements"]


def test_4_band_gap_target(nlp_service):
    text = "Material with band gap around 2.3 eV and high stability"
    res = nlp_service.parse_text(text)
    assert "band_gap" in res["properties"]
    assert res["properties"]["band_gap"].target == 2.3
    assert res["properties"]["band_gap"].unit == "eV"


def test_5_band_gap_range(nlp_service):
    text = "A semiconductor with band gap between 2 and 3 eV"
    res = nlp_service.parse_text(text)
    assert "band_gap" in res["properties"]
    assert res["properties"]["band_gap"].min == 2.0
    assert res["properties"]["band_gap"].max == 3.0
    assert res["properties"]["band_gap"].unit == "eV"


def test_6_energy_above_hull_numerical(nlp_service):
    text = "Crystals with energy above hull below 0.05 eV/atom"
    res = nlp_service.parse_text(text)
    assert "energy_above_hull" in res["properties"]
    assert res["properties"]["energy_above_hull"].max == 0.05
    assert res["properties"]["energy_above_hull"].unit == "eV/atom"


def test_7_qualitative_stability(nlp_service):
    text = "I need a stable material for battery cathodes"
    res = nlp_service.parse_text(text)
    assert "energy_above_hull" in res["properties"]
    # Qualitative preference must NOT invent a numerical threshold
    assert res["properties"]["energy_above_hull"].max is None
    assert res["properties"]["energy_above_hull"].preference in ["stable", "low"]


def test_8_qualitative_ionic_conductivity(nlp_service):
    text = "Solid electrolyte with high ionic conductivity"
    res = nlp_service.parse_text(text)
    assert "ionic_conductivity" in res["properties"]
    assert res["properties"]["ionic_conductivity"].preference == "high"
    assert res["properties"]["ionic_conductivity"].target is None  # no fake number invented


def test_9_application_extraction(nlp_service):
    text = "Looking for a novel battery material based on lithium"
    res = nlp_service.parse_text(text)
    assert "Battery" in res["application"] or "battery" in res["application"].lower()


def test_10_excluded_toxic_shorthand(nlp_service):
    text = "Material with no Pb Cd Hg for clean energy"
    res = nlp_service.parse_text(text)
    assert "Pb" in res["excluded_elements"]
    assert "Cd" in res["excluded_elements"]
    assert "Hg" in res["excluded_elements"]


def test_constraint_normalizer_flow(nlp_service):
    text = "I need a silicon-based energy storage material with a band gap around 2.3 eV and no lead, cadmium or mercury."
    extracted = nlp_service.parse_text(text)
    response = ConstraintNormalizer.normalize(extracted)
    
    assert response.requirements.application == "Energy storage"
    assert "Si" in response.requirements.required_elements
    assert "Pb" in response.requirements.excluded_elements
    assert response.requirements.properties["band_gap"].target == 2.3
    assert response.needs_confirmation is True


def test_11_energy_storage_with_arsenic_exclusion(nlp_service):
    text = "I need a stable silicon-based energy storage material with a band gap between 2.0 and 2.5 eV, low energy above hull, high ionic conductivity, and no Pb, Cd, Hg or As."
    extracted = nlp_service.parse_text(text)
    response = ConstraintNormalizer.normalize(extracted)
    reqs = response.requirements

    assert "Si" in reqs.required_elements
    assert "As" in reqs.excluded_elements
    assert "Pb" in reqs.excluded_elements
    assert "Cd" in reqs.excluded_elements
    assert "Hg" in reqs.excluded_elements
    assert "band_gap" in reqs.properties
    assert reqs.properties["band_gap"].min == 2.0
    assert reqs.properties["band_gap"].max == 2.5
    assert "energy_above_hull" in reqs.properties
    assert "ionic_conductivity" in reqs.properties

