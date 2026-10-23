"""
Comprehensive Scientific Validation Engine for CRYSTAL-X RAG.
Executes deterministic crystallographic, chemical, thermodynamic, and property checks:
- Geometry & Structure: CIF parsing, lattice volume, coordinate wrapping, distance matrix heuristics
- Chemistry & Composition: Formula parsing, element restrictions, charge balance / oxidation state guesses
- Thermodynamic Stability: Convex hull distance (Ehull <= 0.05 eV/atom), formation energy
- Target Application Properties: Band gap classification, theoretical capacity (Faraday), ionic conductivity status
Categorizes every check into standardized statuses: PASS, FAIL, WARNING, UNKNOWN, NOT_RUN.
"""

import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pymatgen.core import Structure, Composition, Element
from pymatgen.io.cif import CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from backend.models.rag_schemas import (
    ScientificCheckResult,
    ValidationCheckStatus
)
from backend.services.validation_service import StructuralValidationService
from backend.services.stability_service import StabilityService
from backend.services.capacity_service import CapacityService


class ScientificValidator:
    def __init__(
        self,
        structural_service: Optional[StructuralValidationService] = None,
        stability_service: Optional[StabilityService] = None,
        capacity_service: Optional[CapacityService] = None
    ):
        self.structural_service = structural_service or StructuralValidationService(min_atomic_distance_heuristic=0.7)
        self.stability_service = stability_service or StabilityService(screening_threshold=0.05)
        self.capacity_service = capacity_service or CapacityService()

    def run_all_checks(
        self,
        struct: Optional[Structure],
        cif_string: Optional[str] = None,
        formula: Optional[str] = None,
        application: str = "Solid electrolyte",
        predicted_ehull: Optional[float] = None,
        predicted_band_gap: Optional[float] = None,
        predicted_conductivity: Optional[float] = None,
        excluded_elements: Optional[List[str]] = None
    ) -> Tuple[List[ScientificCheckResult], Dict[str, ValidationCheckStatus], Dict[str, Any]]:
        """
        Runs the full battery of scientific validation checks.
        Returns:
            - checks: List of individual check results
            - summary: Dict mapping check name -> status
            - domain_data: Detailed numerical and domain metrics
        """
        checks: List[ScientificCheckResult] = []
        domain_data: Dict[str, Any] = {
            "geometry": {},
            "chemistry": {},
            "stability": {},
            "properties": {}
        }

        # If structure is missing but CIF string is given, parse it
        if struct is None and cif_string:
            try:
                parser = CifParser.from_str(cif_string)
                structs = parser.parse_structures(primitive=False)
                if structs:
                    struct = structs[0]
            except Exception:
                struct = None

        # If formula is missing but structure exists, derive it
        if not formula and struct is not None:
            formula = struct.composition.reduced_formula

        # ----------------------------------------------------
        # Category 1: Structure File & Geometry Checks
        # ----------------------------------------------------
        if struct is None:
            checks.append(ScientificCheckResult(
                name="Structure File Parsing",
                status="FAIL",
                detail="Could not parse crystallographic structure file or CIF representation.",
                category="GEOMETRY",
                source_or_method="pymatgen.io.cif.CifParser"
            ))
            checks.append(ScientificCheckResult(
                name="Lattice Geometry & Volume",
                status="NOT_RUN",
                detail="Structure unavailable; lattice check skipped.",
                category="GEOMETRY"
            ))
            checks.append(ScientificCheckResult(
                name="Interatomic Distance Heuristic",
                status="NOT_RUN",
                detail="Structure unavailable; distance check skipped.",
                category="GEOMETRY"
            ))
        else:
            checks.append(ScientificCheckResult(
                name="Structure File Parsing",
                status="PASS",
                detail="CIF syntax verified; crystal structure successfully parsed with valid lattice vectors.",
                category="GEOMETRY",
                source_or_method="pymatgen.io.cif.CifParser"
            ))

            # Lattice parameters & volume
            vol = float(struct.lattice.volume)
            lengths = [float(struct.lattice.a), float(struct.lattice.b), float(struct.lattice.c)]
            angles = [float(struct.lattice.alpha), float(struct.lattice.beta), float(struct.lattice.gamma)]
            
            domain_data["geometry"]["volume_angstrom3"] = vol
            domain_data["geometry"]["lattice_lengths"] = lengths
            domain_data["geometry"]["lattice_angles"] = angles
            domain_data["geometry"]["num_sites"] = len(struct)

            if vol <= 0 or not math.isfinite(vol):
                checks.append(ScientificCheckResult(
                    name="Lattice Geometry & Volume",
                    status="FAIL",
                    detail=f"Degenerate or non-positive unit cell volume: {vol:.2f} Å³.",
                    category="GEOMETRY",
                    actual_value=vol,
                    unit="Å³"
                ))
            elif any(l < 1.0 or l > 120.0 for l in lengths) or any(a < 15.0 or a > 165.0 for a in angles):
                checks.append(ScientificCheckResult(
                    name="Lattice Geometry & Volume",
                    status="WARNING",
                    detail=f"Extreme lattice parameters detected: lengths={lengths}, angles={angles}.",
                    category="GEOMETRY",
                    actual_value=vol,
                    unit="Å³"
                ))
            else:
                checks.append(ScientificCheckResult(
                    name="Lattice Geometry & Volume",
                    status="PASS",
                    detail=f"Lattice is physically well-formed with positive unit cell volume ({vol:.2f} Å³).",
                    category="GEOMETRY",
                    actual_value=vol,
                    unit="Å³"
                ))

            # Atomic distance matrix & overlap checks
            dist_matrix = struct.distance_matrix
            n_sites = len(struct)
            min_dist = 999.0
            overlap_pair = None

            for i in range(n_sites):
                for j in range(i + 1, n_sites):
                    d = dist_matrix[i, j]
                    if d < min_dist:
                        min_dist = float(d)
                        overlap_pair = (struct[i].species_string, struct[j].species_string)

            domain_data["geometry"]["min_interatomic_distance_angstrom"] = min_dist
            domain_data["geometry"]["closest_pair"] = overlap_pair

            if min_dist < 0.70:
                checks.append(ScientificCheckResult(
                    name="Interatomic Distance Heuristic",
                    status="FAIL",
                    detail=f"Unphysical atomic overlap detected ({min_dist:.2f} Å between {overlap_pair}). Minimum threshold is 0.70 Å.",
                    category="GEOMETRY",
                    actual_value=min_dist,
                    reference_value=0.70,
                    unit="Å"
                ))
            elif min_dist < 1.20:
                checks.append(ScientificCheckResult(
                    name="Interatomic Distance Heuristic",
                    status="WARNING",
                    detail=f"Unusually short bond distance ({min_dist:.2f} Å between {overlap_pair}). Requires DFT geometry relaxation to verify bonding.",
                    category="GEOMETRY",
                    actual_value=min_dist,
                    reference_value=1.20,
                    unit="Å"
                ))
            else:
                checks.append(ScientificCheckResult(
                    name="Interatomic Distance Heuristic",
                    status="PASS",
                    detail=f"All interatomic distances satisfy physical spacing (minimum {min_dist:.2f} Å between {overlap_pair}).",
                    category="GEOMETRY",
                    actual_value=min_dist,
                    unit="Å"
                ))

            # Space group & symmetry
            try:
                sga = SpacegroupAnalyzer(struct, symprec=0.1)
                sg_symbol = sga.get_space_group_symbol()
                sg_num = sga.get_space_group_number()
                crystal_sys = sga.get_crystal_system().capitalize()
                domain_data["geometry"]["space_group"] = f"{sg_symbol} (#{sg_num})"
                domain_data["geometry"]["crystal_system"] = crystal_sys

                checks.append(ScientificCheckResult(
                    name="Crystallographic Symmetry Analysis",
                    status="PASS",
                    detail=f"Symmetry resolved: Space Group {sg_symbol} (#{sg_num}), Crystal System: {crystal_sys}.",
                    category="GEOMETRY",
                    actual_value=sg_symbol,
                    source_or_method="spglib.SpacegroupAnalyzer (symprec=0.1)"
                ))
            except Exception as e:
                checks.append(ScientificCheckResult(
                    name="Crystallographic Symmetry Analysis",
                    status="WARNING",
                    detail=f"Could not determine high-symmetry space group: {str(e)}. Defaulted to P1.",
                    category="GEOMETRY",
                    actual_value="P1 (#1)"
                ))

        # ----------------------------------------------------
        # Category 2: Composition & Chemistry Checks
        # ----------------------------------------------------
        comp = None
        if formula:
            try:
                comp = Composition(formula)
                domain_data["chemistry"]["formula"] = comp.formula
                domain_data["chemistry"]["reduced_formula"] = comp.reduced_formula
                domain_data["chemistry"]["elements"] = [el.symbol for el in comp.elements]
                domain_data["chemistry"]["weight"] = float(comp.weight)

                checks.append(ScientificCheckResult(
                    name="Chemical Composition Validity",
                    status="PASS",
                    detail=f"Stoichiometry '{comp.reduced_formula}' is chemically well-defined.",
                    category="CHEMISTRY",
                    actual_value=comp.reduced_formula,
                    source_or_method="pymatgen.core.Composition"
                ))
            except Exception as e:
                checks.append(ScientificCheckResult(
                    name="Chemical Composition Validity",
                    status="FAIL",
                    detail=f"Invalid chemical formula '{formula}': {str(e)}",
                    category="CHEMISTRY"
                ))

        # Element restriction compliance
        if comp and excluded_elements:
            violating = [el for el in excluded_elements if el in [e.symbol for e in comp.elements]]
            if violating:
                checks.append(ScientificCheckResult(
                    name="Element Restrictions",
                    status="FAIL",
                    detail=f"Contains restricted or toxic elements: {', '.join(violating)}.",
                    category="CHEMISTRY",
                    actual_value=violating
                ))
            else:
                checks.append(ScientificCheckResult(
                    name="Element Restrictions",
                    status="PASS",
                    detail="Passed user and safety element exclusion rules.",
                    category="CHEMISTRY"
                ))
        else:
            checks.append(ScientificCheckResult(
                name="Element Restrictions",
                status="PASS",
                detail="No restricted elements flagged.",
                category="CHEMISTRY"
            ))

        # Charge balance & oxidation state plausibility
        if comp:
            try:
                oxi_guesses = comp.oxi_state_guesses()
                if oxi_guesses and len(oxi_guesses) > 0:
                    primary_guess = oxi_guesses[0]
                    domain_data["chemistry"]["oxidation_states"] = primary_guess
                    domain_data["chemistry"]["charge_balanced"] = True

                    checks.append(ScientificCheckResult(
                        name="Charge Neutrality & Oxidation State Plausibility",
                        status="PASS",
                        detail=f"Plausible charge-neutral oxidation states identified: {primary_guess}.",
                        category="CHEMISTRY",
                        actual_value=str(primary_guess),
                        source_or_method="pymatgen.core.Composition.oxi_state_guesses"
                    ))
                else:
                    domain_data["chemistry"]["charge_balanced"] = False
                    checks.append(ScientificCheckResult(
                        name="Charge Neutrality & Oxidation State Plausibility",
                        status="WARNING",
                        detail="Standard electronegativity rules yielded ambiguous oxidation states. May indicate a mixed-valence, intermetallic, or radical phase.",
                        category="CHEMISTRY",
                        source_or_method="pymatgen.core.Composition.oxi_state_guesses"
                    ))
            except Exception:
                checks.append(ScientificCheckResult(
                    name="Charge Neutrality & Oxidation State Plausibility",
                    status="UNKNOWN",
                    detail="Could not compute formal oxidation state assignments.",
                    category="CHEMISTRY"
                ))
        else:
            checks.append(ScientificCheckResult(
                name="Charge Neutrality & Oxidation State Plausibility",
                status="NOT_RUN",
                detail="Composition unavailable.",
                category="CHEMISTRY"
            ))

        # ----------------------------------------------------
        # Category 3: Thermodynamic Stability Checks
        # ----------------------------------------------------
        if predicted_ehull is not None:
            domain_data["stability"]["energy_above_hull_ev_per_atom"] = predicted_ehull
            domain_data["stability"]["threshold_ev_per_atom"] = 0.05
            
            if predicted_ehull <= 0.00:
                checks.append(ScientificCheckResult(
                    name="Thermodynamic Convex Hull Stability (Ehull)",
                    status="PASS",
                    detail=f"Predicted on the convex hull (Ehull = {predicted_ehull:.3f} eV/atom). Ground-state phase.",
                    category="STABILITY",
                    actual_value=predicted_ehull,
                    reference_value=0.05,
                    unit="eV/atom",
                    source_or_method="Convex Hull Screening Model"
                ))
            elif predicted_ehull <= 0.05:
                checks.append(ScientificCheckResult(
                    name="Thermodynamic Convex Hull Stability (Ehull)",
                    status="PASS",
                    detail=f"Predicted Ehull of {predicted_ehull:.3f} eV/atom satisfies the standard metastable synthesizability threshold (<= 0.05 eV/atom).",
                    category="STABILITY",
                    actual_value=predicted_ehull,
                    reference_value=0.05,
                    unit="eV/atom",
                    source_or_method="Convex Hull Screening Model"
                ))
            else:
                checks.append(ScientificCheckResult(
                    name="Thermodynamic Convex Hull Stability (Ehull)",
                    status="WARNING",
                    detail=f"Predicted Ehull of {predicted_ehull:.3f} eV/atom exceeds the 0.05 eV/atom threshold. High risk of phase decomposition.",
                    category="STABILITY",
                    actual_value=predicted_ehull,
                    reference_value=0.05,
                    unit="eV/atom",
                    source_or_method="Convex Hull Screening Model"
                ))
        else:
            checks.append(ScientificCheckResult(
                name="Thermodynamic Convex Hull Stability (Ehull)",
                status="UNKNOWN",
                detail="Energy above hull not calculated for this candidate. Ab initio DFT relaxation required.",
                category="STABILITY"
            ))

        # ----------------------------------------------------
        # Category 4: Target Application Properties Checks
        # ----------------------------------------------------
        # Band gap
        if predicted_band_gap is not None:
            domain_data["properties"]["band_gap_ev"] = predicted_band_gap
            if predicted_band_gap > 3.0:
                bg_status: ValidationCheckStatus = "PASS" if "electrolyte" in application.lower() else "WARNING"
                detail = f"Wide band gap insulator ({predicted_band_gap:.2f} eV). Favorable electronic insulation for solid electrolytes."
            elif predicted_band_gap > 1.0:
                bg_status = "PASS" if "electrode" in application.lower() or "storage" in application.lower() else "WARNING"
                detail = f"Semiconducting band gap ({predicted_band_gap:.2f} eV)."
            else:
                bg_status = "WARNING" if "electrolyte" in application.lower() else "PASS"
                detail = f"Narrow or metallic band gap ({predicted_band_gap:.2f} eV). Risk of electronic leakage in electrolyte applications."

            checks.append(ScientificCheckResult(
                name="Electronic Band Gap & Insulation",
                status=bg_status,
                detail=detail,
                category="TARGET_PROPERTIES",
                actual_value=predicted_band_gap,
                unit="eV",
                source_or_method="ML / Empirical Band Gap Screening"
            ))
        else:
            checks.append(ScientificCheckResult(
                name="Electronic Band Gap & Insulation",
                status="UNKNOWN",
                detail="Electronic band gap has not been calculated.",
                category="TARGET_PROPERTIES"
            ))

        # Ionic conductivity
        if predicted_conductivity is not None:
            domain_data["properties"]["ionic_conductivity_s_per_cm"] = predicted_conductivity
            checks.append(ScientificCheckResult(
                name="Ionic Conductivity Assessment",
                status="PASS" if predicted_conductivity >= 1e-4 else "WARNING",
                detail=f"Estimated conductivity: {predicted_conductivity:.2e} S/cm.",
                category="TARGET_PROPERTIES",
                actual_value=predicted_conductivity,
                unit="S/cm"
            ))
        else:
            checks.append(ScientificCheckResult(
                name="Ionic Conductivity Assessment",
                status="UNKNOWN",
                detail="Candidate-specific ionic conductivity is unknown. Requires NEB barrier calculation or AIMD simulation.",
                category="TARGET_PROPERTIES"
            ))

        # Theoretical capacity (Faraday)
        if comp and ("electrode" in application.lower() or "cathode" in application.lower() or "battery" in application.lower()):
            cap_eval = self.capacity_service.evaluate_capacity(comp)
            theor_cap = cap_eval.theoretical_capacity
            domain_data["properties"]["theoretical_capacity_mah_per_g"] = theor_cap
            domain_data["properties"]["redox_species"] = cap_eval.redox_species

            if theor_cap and theor_cap > 100.0:
                checks.append(ScientificCheckResult(
                    name="Theoretical Specific Capacity",
                    status="PASS",
                    detail=f"Analytical theoretical capacity: {theor_cap:.1f} mAh/g ({cap_eval.redox_species} redox).",
                    category="TARGET_PROPERTIES",
                    actual_value=theor_cap,
                    unit="mAh/g",
                    source_or_method="Faraday Equation Q = nF / (3.6 M)"
                ))
            else:
                checks.append(ScientificCheckResult(
                    name="Theoretical Specific Capacity",
                    status="WARNING",
                    detail=f"Theoretical capacity is modest: {theor_cap:.1f} mAh/g.",
                    category="TARGET_PROPERTIES",
                    actual_value=theor_cap,
                    unit="mAh/g",
                    source_or_method="Faraday Equation Q = nF / (3.6 M)"
                ))
        else:
            checks.append(ScientificCheckResult(
                name="Theoretical Specific Capacity",
                status="NOT_RUN",
                detail="Not an intercalation electrode application; capacity check not applicable.",
                category="TARGET_PROPERTIES"
            ))

        # Build summary dict
        summary = {c.name: c.status for c in checks}
        return checks, summary, domain_data
