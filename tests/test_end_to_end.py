"""
End-to-End Demonstration Scenario Test for CRYSTAL-X.
Verifies the complete pipeline:
User natural language input
  ↓
NLP requirement extraction
  ↓
Structured constraints normalization & review confirmation
  ↓
Crystal generation (MatterGen / Demo)
  ↓
Structural validation (pymatgen, wrapping, atom overlap heuristic)
  ↓
Property screening (hard constraints, provenance)
  ↓
Multi-criteria ranking (weight renormalization)
  ↓
Downstream DFT queue & package export
"""

import pytest
from backend.services.nlp_requirement_service import NLPRequirementService
from backend.services.constraint_normalizer import ConstraintNormalizer
from backend.services.demo_generator import DemoCrystalGenerator
from backend.services.validation_service import StructuralValidationService
from backend.services.screening_service import PropertyScreeningService
from backend.services.ranking_service import MultiCriteriaRankingEngine
from backend.services.dft_service import DFTQueueService
from backend.models.schemas import DFTQueueItem


def test_complete_end_to_end_demonstration_scenario():
    user_prompt = (
        "I need a silicon-based energy storage material with a band gap around 2.3 eV, "
        "low energy above hull, high ionic conductivity, and no lead, cadmium or mercury."
    )

    # 1. NLP Extraction
    nlp_service = NLPRequirementService()
    extracted = nlp_service.parse_text(user_prompt)

    assert "Si" in extracted["required_elements"]
    assert "Pb" in extracted["excluded_elements"]
    assert "Cd" in extracted["excluded_elements"]
    assert "Hg" in extracted["excluded_elements"]
    assert extracted["properties"]["band_gap"].target == 2.3
    assert extracted["properties"]["energy_above_hull"].preference == "low"
    assert extracted["properties"]["ionic_conductivity"].preference == "high"

    # 2. Constraint Normalization & Confirmation
    normalized_res = ConstraintNormalizer.normalize(extracted)
    reqs = normalized_res.requirements
    assert normalized_res.needs_confirmation is True

    # User confirms requirements (possibly tuning candidate count to 6)
    reqs.num_candidates = 6
    validation_check = ConstraintNormalizer.validate_requirements(reqs)
    assert validation_check.is_valid is True

    # 3. Crystal Generation
    generator = DemoCrystalGenerator()
    raw_candidates = generator.generate(reqs, reqs.num_candidates)
    assert len(raw_candidates) == 6
    assert all(c["generation_mode"] == "DEMO_GENERATOR" for c in raw_candidates)

    # 4. Structural Validation
    validator = StructuralValidationService(min_atomic_distance_heuristic=0.7)
    screening_service = PropertyScreeningService()
    seen_structs = []

    processed = []
    for raw in raw_candidates:
        cand_id = raw["candidate_id"]
        cif_str = raw["raw_cif"]
        struct = raw["structure"]

        val_res = validator.validate_structure(struct, cif_str, requirements=reqs, existing_structures=seen_structs)
        if not val_res.is_duplicate:
            seen_structs.append((cand_id, struct))

        preds = screening_service.predict_properties(struct, generator_mode="DEMO_GENERATOR")
        screen_res = screening_service.screen_candidate(struct, preds, reqs)
        ranking_res = MultiCriteriaRankingEngine.calculate_score(preds, val_res, reqs)

        processed.append({
            "cand_id": cand_id,
            "struct": struct,
            "validation": val_res,
            "predictions": preds,
            "screening": screen_res,
            "ranking": ranking_res
        })

    # Verify that constraints reached validation:
    # Any candidate containing excluded elements or missing Si is marked INVALID
    for p in processed:
        struct_elems = set(e.symbol for e in p["struct"].composition.elements)
        if "Pb" in struct_elems or "Cd" in struct_elems or "Hg" in struct_elems:
            assert p["validation"].is_valid is False
        if "Si" not in struct_elems:
            assert p["validation"].is_valid is False

    # 5. Ranking Verification
    # Check that ionic conductivity is honest (NOT_AVAILABLE) and ranking did not assign 0
    top_cand = max(processed, key=lambda x: x["ranking"].total_score)
    assert top_cand["predictions"].ionic_conductivity.source == "NOT_AVAILABLE"
    assert top_cand["ranking"].conductivity_score is None
    assert top_cand["ranking"].total_score > 0.0
    assert "renormalized" in top_cand["ranking"].ranking_notes[0].lower()

    # 6. Downstream DFT Queue
    dft_service = DFTQueueService()
    dft_item = DFTQueueItem(
        candidate_id=top_cand["cand_id"],
        formula=top_cand["struct"].composition.reduced_formula,
        status="Ready for DFT",
        predicted_properties={
            "energy_above_hull": top_cand["predictions"].energy_above_hull.value,
            "band_gap": top_cand["predictions"].band_gap.value
        },
        ranking_score=top_cand["ranking"].total_score,
        reason_selected="Top ranked candidate in NLP discovery run",
        cif_string=top_cand["struct"].to(fmt="cif"),
        added_at="2026-09-20T12:00:00"
    )
    dft_service.add_to_queue(dft_item)
    assert dft_service.is_in_queue(top_cand["cand_id"]) is True

    # Export DFT package
    export_res = dft_service.export_package()
    assert top_cand["cand_id"] in export_res.exported_candidates
    assert "downstream" in export_res.disclaimer.lower()
