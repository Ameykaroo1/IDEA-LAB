"""
Phenomena Router Service for CRYSTAL-X.
Determines how every requested physical, chemical, and electrochemical phenomenon
should be evaluated across available computational pipelines:
- MatterGen conditioning (if supported by checkpoint)
- MatterSim / ML Force Fields
- Dedicated ML property models
- Analytical / Faraday formulations
- Structural relaxation & geometric simulation
- Downstream DFT / NEB queue

CRITICAL RULE:
Never pretends that a single model predicts every property.
Every phenomenon is routed to an appropriate method or honestly marked as NOT_AVAILABLE / REQUIRES_DFT.
"""

from typing import Dict, Any, List, Optional
from backend.models.schemas import MaterialRequirements, PropertyConstraint


class PhenomenonRoute:
    def __init__(
        self,
        phenomenon: str,
        target_method: str,
        fallback_method: str,
        is_hard_constraint: bool,
        provenance_target: str,
        status_if_unavailable: str = "NOT_AVAILABLE",
        notes: str = ""
    ):
        self.phenomenon = phenomenon
        self.target_method = target_method
        self.fallback_method = fallback_method
        self.is_hard_constraint = is_hard_constraint
        self.provenance_target = provenance_target
        self.status_if_unavailable = status_if_unavailable
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phenomenon": self.phenomenon,
            "target_method": self.target_method,
            "fallback_method": self.fallback_method,
            "is_hard_constraint": self.is_hard_constraint,
            "provenance_target": self.provenance_target,
            "status_if_unavailable": self.status_if_unavailable,
            "notes": self.notes
        }


class PhenomenaRouter:
    """
    Analyzes user requirements and maps every requested phenomenon to a viable computational route.
    """
    def __init__(self, mattersim_available: bool = False, mattergen_available: bool = False):
        self.mattersim_available = mattersim_available
        self.mattergen_available = mattergen_available

    def route_requirements(self, requirements: MaterialRequirements) -> Dict[str, PhenomenonRoute]:
        """
        Builds a execution plan for all user-requested phenomena.
        """
        routes: Dict[str, PhenomenonRoute] = {}

        # 1. Band Gap
        bg_req = requirements.properties.get("band_gap")
        is_bg_hard = (bg_req is not None and (bg_req.min is not None or bg_req.max is not None or bg_req.type == "hard_constraint"))
        routes["band_gap"] = PhenomenonRoute(
            phenomenon="band_gap",
            target_method="MatterGen_Conditioning" if self.mattergen_available else "ML_BandGap_Predictor",
            fallback_method="Empirical_Surrogate",
            is_hard_constraint=is_bg_hard,
            provenance_target="MATTERGEN" if self.mattergen_available else "ML_MODEL",
            status_if_unavailable="NOT_AVAILABLE",
            notes="Evaluated via conditioned generation if supported, otherwise ML predictor or surrogate."
        )

        # 2. Energy Above Hull (Thermodynamic Stability)
        ehull_req = requirements.properties.get("energy_above_hull")
        is_ehull_hard = (ehull_req is not None and (ehull_req.max is not None or ehull_req.type == "hard_constraint"))
        routes["energy_above_hull"] = PhenomenonRoute(
            phenomenon="energy_above_hull",
            target_method="MatterSim_ML_Force_Field" if self.mattersim_available else "Project_Screening_Surrogate",
            fallback_method="DFT_Validation_Queue",
            is_hard_constraint=is_ehull_hard,
            provenance_target="MATTERSIM" if self.mattersim_available else "DEMO_SURROGATE",
            status_if_unavailable="NOT_AVAILABLE",
            notes="MatterSim relaxation / convex hull construction against MP-20 reference hull."
        )

        # 3. Ionic Conductivity
        cond_req = requirements.properties.get("ionic_conductivity")
        is_cond_hard = (cond_req is not None and (cond_req.min is not None or cond_req.type == "hard_constraint"))
        routes["ionic_conductivity"] = PhenomenonRoute(
            phenomenon="ionic_conductivity",
            target_method="Calibrated_ML_Conductivity_Model",
            fallback_method="Structural_Percolation_Analysis",
            is_hard_constraint=is_cond_hard,
            provenance_target="ML_MODEL",
            status_if_unavailable="NOT_AVAILABLE",
            notes="Separates ion pathway detection from quantitative conductivity prediction."
        )

        # 4. Ion Migration & Migration Barrier
        routes["ion_migration"] = PhenomenonRoute(
            phenomenon="ion_migration",
            target_method="Geometric_Percolation_Pathway_Analysis",
            fallback_method="DFT_NEB_Queue",
            is_hard_constraint=False,
            provenance_target="ANALYTICAL",
            status_if_unavailable="REQUIRES_DFT",
            notes="Detects mobile ion channels. Accurate barrier requires downstream DFT/NEB."
        )

        # 5. Volume Change
        vol_req = requirements.properties.get("volume_change")
        is_vol_hard = (vol_req is not None and (vol_req.max is not None or vol_req.type == "hard_constraint"))
        routes["volume_change"] = PhenomenonRoute(
            phenomenon="volume_change",
            target_method="Ion_Insertion_Lattice_Relaxation",
            fallback_method="Empirical_Volume_Surrogate",
            is_hard_constraint=is_vol_hard,
            provenance_target="ANALYTICAL",
            status_if_unavailable="NOT_AVAILABLE",
            notes="Calculates (V_final - V_initial) / V_initial * 100% upon mobile species deinsertion."
        )

        # 6. Theoretical Specific Capacity
        cap_req = requirements.properties.get("capacity")
        is_cap_hard = (cap_req is not None and (cap_req.min is not None or cap_req.type == "hard_constraint"))
        routes["capacity"] = PhenomenonRoute(
            phenomenon="capacity",
            target_method="Analytical_Faraday_Equation",
            fallback_method="NOT_AVAILABLE",
            is_hard_constraint=is_cap_hard,
            provenance_target="ANALYTICAL",
            status_if_unavailable="NOT_AVAILABLE",
            notes="Q = nF / (3.6 * M). Explicitly labeled as theoretical capacity."
        )

        return routes
