"""
Constraint Normalizer for CRYSTAL-X.
Normalizes extracted requirements into the unified schema, handling unit conversions,
qualitative preferences, and preparing data for user review and generator consumption.
"""

from typing import Dict, Any, List, Optional
from backend.models.schemas import (
    MaterialRequirements,
    PropertyConstraint,
    StructuralConstraints,
    RankingWeights,
    ParseResponse,
    ValidateRequirementsResponse
)


class ConstraintNormalizer:
    @staticmethod
    def normalize(extracted_data: Dict[str, Any]) -> ParseResponse:
        """
        Takes the dictionary from NLPRequirementService and builds a normalized ParseResponse.
        """
        raw_text = extracted_data.get("raw_text", "")
        application = extracted_data.get("application", "Energy storage")
        energy_domain = extracted_data.get("energy_domain", "BATTERY")
        battery_type = extracted_data.get("battery_type", None)
        required_elements = extracted_data.get("required_elements", [])
        preferred_elements = extracted_data.get("preferred_elements", [])
        allowed_elements = extracted_data.get("allowed_elements", [])
        excluded_elements = extracted_data.get("excluded_elements", [])
        raw_props = extracted_data.get("properties", {})
        confidences = extracted_data.get("confidences", {})
        ambiguities = list(extracted_data.get("ambiguities", []))
        warnings = list(extracted_data.get("warnings", []))
        steps = extracted_data.get("extraction_steps", [])

        # Normalize properties
        normalized_props: Dict[str, PropertyConstraint] = {}
        for prop_name, constraint in raw_props.items():
            if isinstance(constraint, PropertyConstraint):
                normalized_props[prop_name] = constraint
            elif isinstance(constraint, dict):
                normalized_props[prop_name] = PropertyConstraint(**constraint)

        # Build dynamic default ranking weights based on user emphasis
        stability_wt = 0.4
        bandgap_wt = 0.3
        conductivity_wt = 0.2
        chemistry_wt = 0.1

        if "ionic_conductivity" in normalized_props:
            conductivity_wt = 0.3
            stability_wt = 0.35
            bandgap_wt = 0.25
            chemistry_wt = 0.1
        elif "band_gap" in normalized_props:
            bandgap_wt = 0.4
            stability_wt = 0.4
            conductivity_wt = 0.1
            chemistry_wt = 0.1

        weights = RankingWeights(
            stability=round(stability_wt, 2),
            band_gap=round(bandgap_wt, 2),
            ionic_conductivity=round(conductivity_wt, 2),
            chemistry=round(chemistry_wt, 2)
        )

        material_type = extracted_data.get("material_type", None)
        if not material_type and battery_type:
            material_type = battery_type.replace("_", " ")

        reqs = MaterialRequirements(
            application=application,
            energy_domain=energy_domain,
            battery_type=battery_type,
            material_type=material_type,
            required_elements=required_elements,
            preferred_elements=preferred_elements,
            allowed_elements=allowed_elements,
            excluded_elements=excluded_elements,
            properties=normalized_props,
            band_gap=normalized_props.get("band_gap"),
            energy_above_hull=normalized_props.get("energy_above_hull"),
            ionic_conductivity=normalized_props.get("ionic_conductivity"),
            structural_constraints=StructuralConstraints(),
            ranking_weights=weights,
            num_candidates=10
        )

        return ParseResponse(
            raw_text=raw_text,
            requirements=reqs,
            confidences=confidences,
            ambiguities=ambiguities,
            warnings=warnings,
            needs_confirmation=True,
            extraction_steps=steps
        )

    @staticmethod
    def validate_requirements(reqs: MaterialRequirements) -> ValidateRequirementsResponse:
        """
        Validates reviewed/confirmed requirements before generation begins.
        """
        errors = []
        warnings = []

        # Check element overlap between required and excluded
        overlap = set(reqs.required_elements).intersection(set(reqs.excluded_elements))
        if overlap:
            errors.append(f"Contradictory constraints: Element(s) {list(overlap)} cannot be both required and excluded.")

        # Check weights sum
        w = reqs.ranking_weights
        total_w = w.stability + w.band_gap + w.ionic_conductivity + w.chemistry
        if abs(total_w - 1.0) > 0.05 and total_w > 0:
            warnings.append(f"Ranking weights sum to {total_w:.2f} (will be auto-normalized to 1.0 during ranking).")

        # Check candidate range
        if reqs.num_candidates < 1 or reqs.num_candidates > 100:
            errors.append("Number of candidates must be between 1 and 100.")

        is_valid = len(errors) == 0
        return ValidateRequirementsResponse(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
