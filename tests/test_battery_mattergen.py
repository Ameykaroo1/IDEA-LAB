"""
Rigorous validation test suite for CRYSTAL-X battery & clean-energy generative platform.
Tests:
1. Master prompt NLP extraction (Li, Si, band gap 1.5-2.2 eV, hull < 0.03 eV/atom, As/Pb/Cd/Hg excluded).
2. Hard constraints vs soft preferences strict tagging.
3. MatterGen adapter condition mapping & truthful status reporting.
4. Separate partition of rejected candidates with explicit rejection reasons.
5. Dynamic requirement match scoring and 'Why this candidate ranked here' checklist.
6. Unified MP-20 and JARVIS-DFT reference dataset status.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.nlp_requirement_service import NLPRequirementService
from backend.services.constraint_normalizer import ConstraintNormalizer
from backend.services.mattergen_adapter import MatterGenAdapter
from backend.services.novelty_service import NoveltyService

client = TestClient(app)

MASTER_PROMPT = (
    "Find a crystalline energy-storage material containing Si and Li with a band gap "
    "between 1.5 and 2.2 eV, energy above hull below 0.03 eV/atom, high ionic conductivity, "
    "high capacity, and less than 5% volume change. Pb, Cd, Hg, and As must be completely excluded."
)

def test_master_prompt_nlp_extraction():
    nlp = NLPRequirementService()
    parsed = nlp.parse_text(MASTER_PROMPT)
    normalized = ConstraintNormalizer.normalize(parsed)
    reqs = normalized.requirements

    # Required & excluded elements
    assert "Li" in reqs.required_elements
    assert "Si" in reqs.required_elements
    assert set(["Pb", "Cd", "Hg", "As"]).issubset(set(reqs.excluded_elements))

    # Domain & battery type
    assert reqs.energy_domain in ["BATTERY", "IONIC_CONDUCTOR", "ENERGY_STORAGE"]
    assert reqs.battery_type == "lithium_ion"

    # Band gap: hard constraint
    bg = reqs.properties.get("band_gap")
    assert bg is not None
    assert bg.type == "hard_constraint"
    assert bg.min == 1.5
    assert bg.max == 2.2

    # Energy above hull: hard constraint
    hull = reqs.properties.get("energy_above_hull")
    assert hull is not None
    assert hull.type == "hard_constraint"
    assert hull.max == 0.03

    # Volume change: hard constraint
    vol = reqs.properties.get("volume_change")
    assert vol is not None
    assert vol.type == "hard_constraint"
    assert vol.max == 5.0

    # Ionic conductivity: soft preference
    cond = reqs.properties.get("ionic_conductivity")
    assert cond is not None
    assert cond.type == "soft_preference"
    assert cond.min is None
    assert cond.max is None

    # Capacity: soft preference
    cap = reqs.properties.get("capacity")
    assert cap is not None
    assert cap.type == "soft_preference"
    assert cap.min is None
    assert cap.max is None


def test_mattergen_adapter_status_and_condition_mapping():
    adapter = MatterGenAdapter()
    status = adapter.get_model_status()
    
    # In Windows / CPU environment without installed MatterGen
    assert status["status"] == "NOT CONFIGURED"
    assert status["generator"] == "LOCAL DEMO"
    assert "DEMO GENERATION MODE" in status["notice"]

    # Condition mapping
    nlp = NLPRequirementService()
    parsed = nlp.parse_text(MASTER_PROMPT)
    normalized = ConstraintNormalizer.normalize(parsed)
    conditions, supported, unsupported = adapter.map_requirements_to_conditions(normalized.requirements)

    assert "target_elements" in conditions
    # Unsupported properties must be reported downstream
    assert any("Ionic Conductivity" in u for u in unsupported)
    assert any("Capacity" in u for u in unsupported)
    assert any("Volume Change" in u for u in unsupported)


def test_master_prompt_end_to_end_discovery():
    nlp = NLPRequirementService()
    parsed = nlp.parse_text(MASTER_PROMPT)
    normalized = ConstraintNormalizer.normalize(parsed)

    res = client.post("/api/discover", json={"requirements": normalized.requirements.dict()})
    assert res.status_code == 200
    data = res.json()

    # Total candidates generated
    total_generated = len(data["candidates"]) + len(data["rejected_candidates"])
    assert total_generated == 10

    # Passing candidates
    assert len(data["candidates"]) > 0
    for cand in data["candidates"]:
        assert cand["structural_status"] == "VALID"
        assert cand["requirement_compliance"] == "MATCH"
        assert "Li" in cand["elements"]
        assert "Si" in cand["elements"]
        assert not any(ex in cand["elements"] for ex in ["Pb", "Cd", "Hg", "As"])
        # Explanation checklist is populated
        assert len(cand.get("ranking_explanation", [])) >= 2
        # Property provenance is recorded
        assert "energy_above_hull" in cand["property_provenance"]
        assert "band_gap" in cand["property_provenance"]

    # Rejected candidates partition
    assert len(data["rejected_candidates"]) > 0
    for rej in data["rejected_candidates"]:
        assert rej["requirement_compliance"] == "REJECTED" or rej["structural_status"] == "INVALID"
        assert rej["rejection_reason"] is not None
        assert len(rej["rejection_reason"]) > 0


def test_api_status_endpoints():
    res_model = client.get("/api/model/status")
    assert res_model.status_code == 200
    model_data = res_model.json()
    assert "status" in model_data
    assert "generator" in model_data

    res_datasets = client.get("/api/datasets/status")
    assert res_datasets.status_code == 200
    dataset_data = res_datasets.json()
    assert "mp20" in dataset_data
    assert "jarvis" in dataset_data
    assert dataset_data["total_reference_structures"] >= 5
