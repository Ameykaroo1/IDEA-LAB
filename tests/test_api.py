"""
API Integration Tests for CRYSTAL-X FastAPI backend.
Covers:
- POST /api/requirements/parse (valid, empty, ambiguous, missing numbers)
- POST /api/requirements/validate
- POST /api/discover
- POST /api/rank
- POST /api/upload-cif
- POST /api/dft-queue & export
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_api_parse_valid():
    payload = {
        "text": "I need a silicon-based energy storage material with a band gap around 2.3 eV and no lead, cadmium or mercury."
    }
    res = client.post("/api/requirements/parse", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "Si" in data["requirements"]["required_elements"]
    assert "Pb" in data["requirements"]["excluded_elements"]
    assert data["requirements"]["properties"]["band_gap"]["target"] == 2.3
    assert data["needs_confirmation"] is True


def test_api_parse_empty():
    payload = {"text": "   "}
    res = client.post("/api/requirements/parse", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["ambiguities"]) > 0


def test_api_parse_ambiguous_and_missing_numbers():
    payload = {"text": "I want a stable material with high conductivity."}
    res = client.post("/api/requirements/parse", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert any("threshold" in amb.lower() for amb in data["ambiguities"])


def test_api_validate_requirements():
    # Valid
    valid_payload = {
        "requirements": {
            "application": "Battery",
            "required_elements": ["Si"],
            "excluded_elements": ["Pb"],
            "num_candidates": 10
        }
    }
    res = client.post("/api/requirements/validate", json=valid_payload)
    assert res.status_code == 200
    assert res.json()["is_valid"] is True

    # Contradictory (Si is both required and excluded)
    invalid_payload = {
        "requirements": {
            "application": "Battery",
            "required_elements": ["Si"],
            "excluded_elements": ["Si"],
            "num_candidates": 10
        }
    }
    res = client.post("/api/requirements/validate", json=invalid_payload)
    assert res.status_code == 200
    assert res.json()["is_valid"] is False
    assert len(res.json()["errors"]) > 0


def test_api_discover_and_candidates():
    payload = {
        "requirements": {
            "application": "Energy storage",
            "required_elements": ["Si"],
            "excluded_elements": ["Pb", "Cd", "Hg"],
            "properties": {
                "band_gap": {"target": 2.3, "tolerance": 0.5, "unit": "eV"}
            },
            "num_candidates": 5
        },
        "generator_mode": "demo"
    }
    res = client.post("/api/discover", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert len(data["candidates"]) + len(data["rejected_candidates"]) == 5
    assert len(data["candidates"]) > 0
    assert data["generator_mode"] == "DEMO_GENERATOR"

    # List candidates endpoint
    res_list = client.get("/api/candidates")
    assert res_list.status_code == 200
    cands = res_list.json()
    assert len(cands) >= 5

    # Specific candidate endpoint
    cand_id = cands[0]["candidate_id"]
    res_single = client.get(f"/api/candidates/{cand_id}")
    assert res_single.status_code == 200
    assert res_single.json()["candidate_id"] == cand_id


def test_api_re_rank():
    # Discover first to populate
    client.post("/api/discover", json={
        "requirements": {"application": "Energy storage", "required_elements": ["Si"], "num_candidates": 5},
        "generator_mode": "demo"
    })
    
    payload = {
        "weights": {
            "stability": 0.9,
            "band_gap": 0.05,
            "ionic_conductivity": 0.0,
            "chemistry": 0.05
        }
    }
    res = client.post("/api/rank", json=payload)
    assert res.status_code == 200
    cands = res.json()
    assert len(cands) >= 5
    # Verify effective weights recalculated
    eff_w = cands[0]["ranking"]["effective_weights"]
    assert "stability" in eff_w


def test_api_upload_cif():
    sample_cif = """data_test
_cell_length_a 4.00
_cell_length_b 4.00
_cell_length_c 4.00
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0.0 0.0 0.0
"""
    files = {"file": ("test_si.cif", sample_cif.encode("utf-8"), "chemical/x-cif")}
    res = client.post("/api/upload-cif", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["candidate"]["reduced_formula"] == "Si"
    assert data["candidate"]["validation"]["status"] == "VALID"


def test_api_dft_queue():
    # Discover candidates
    disc = client.post("/api/discover", json={
        "requirements": {"application": "Battery", "required_elements": ["Si"], "num_candidates": 3}
    }).json()
    cand_id = disc["candidates"][0]["candidate_id"]

    # Add to DFT queue
    add_res = client.post("/api/dft-queue", data={"candidate_id": cand_id, "reason": "High ranking"})
    assert add_res.status_code == 200

    # Get queue
    q_res = client.get("/api/dft-queue")
    assert q_res.status_code == 200
    items = q_res.json()
    assert any(it["candidate_id"] == cand_id for it in items)

    # Export queue package
    exp_res = client.post("/api/dft-queue/export")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert cand_id in exp_data["exported_candidates"]
    assert "downstream" in exp_data["disclaimer"]
