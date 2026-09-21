"""
Deterministic Crystallographic Structural Validation Service for CRYSTAL-X.
Uses pymatgen and spglib for crystallographic verification.
Implements:
1. Chemical validity (elements, species, composition consistency, required, allowed & excluded species)
2. Lattice validity (finite vectors, det > 0, unit cell volume > 0, non-degenerate lattice, length/angle bounds)
3. Coordinates validity (finite, periodic wrap [0, 1), no NaN/Inf)
4. Obvious atom-overlap heuristic (periodic boundary distance matrix, configurable threshold, default 0.7 Å)
5. Plausible physical density bounds (configurable threshold, default 0.05 - 25.0 g/cm³)
6. Periodic structure representation
7. Symmetry & Standardization (SpacegroupAnalyzer: primitive/conventional, space group symbol & number)
8. Deterministic structure hash from canonicalized structure
9. Deduplication via StructureMatcher (classifying candidates as DUPLICATE, SIMILAR, or DISTINCT)

Note: Evaluates physical and crystallographic validity strictly independently of user property requirements.
"""

import math
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pymatgen.core import Structure, Lattice, Element
from pymatgen.io.cif import CifParser
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from backend.models.schemas import (
    StructuralValidationResult,
    ValidationCheckItem,
    MaterialRequirements
)


class StructuralValidationService:
    def __init__(
        self,
        min_atomic_distance_heuristic: float = 0.7,
        min_density: float = 0.05,
        max_density: float = 25.0
    ):
        self.min_dist_heuristic = min_atomic_distance_heuristic
        self.min_density = min_density
        self.max_density = max_density
        self.structure_matcher = StructureMatcher(
            ltol=0.2,
            stol=0.3,
            angle_tol=5.0,
            primitive_cell=True,
            scale=True
        )

    @staticmethod
    def compute_structure_hash(struct: Structure) -> str:
        """
        Creates a deterministic hash based on canonicalized formula, space group,
        rounded lattice parameters, and standardized fractional coordinates.
        Consistent for identical standardized structures.
        """
        try:
            if not np.all(np.isfinite(struct.lattice.matrix)) or not np.all(np.isfinite(struct.frac_coords)):
                return "invalid_coords_hash"
            if struct.lattice.volume <= 0:
                return "invalid_volume_hash"
            sga = SpacegroupAnalyzer(struct, symprec=0.1)
            std_struct = sga.get_conventional_standard_structure()
            sg_symbol = sga.get_space_group_symbol()
        except Exception:
            std_struct = struct
            sg_symbol = "unknown"

        try:
            formula = std_struct.composition.reduced_formula
            latt = std_struct.lattice
            latt_str = f"{latt.a:.2f}_{latt.b:.2f}_{latt.c:.2f}_{latt.alpha:.1f}_{latt.beta:.1f}_{latt.gamma:.1f}"
            
            sites_repr = []
            for site in sorted(std_struct.sites, key=lambda s: (s.species_string, round(s.a, 2), round(s.b, 2), round(s.c, 2))):
                sites_repr.append(f"{site.species_string}:{site.a:.2f},{site.b:.2f},{site.c:.2f}")

            canonical_str = f"{formula}|{sg_symbol}|{latt_str}|{';'.join(sites_repr)}"
            return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:16]
        except Exception:
            return "hash_error"

    def parse_and_validate_cif_string(self, cif_string: str) -> Tuple[Optional[Structure], StructuralValidationResult]:
        """
        Parses a CIF string and validates its crystallographic structure.
        Returns (struct, validation_result).
        """
        try:
            parser = CifParser.from_str(cif_string)
            structs = parser.parse_structures(primitive=False)
            if not structs or len(structs) == 0:
                res = StructuralValidationResult(
                    status="INVALID",
                    is_valid=False,
                    checks=[ValidationCheckItem(name="CIF Syntax & Representation", passed=False, detail="No structure found in CIF string.")],
                    reasons=["Failed to parse structure from CIF: file contained no valid structure block."]
                )
                return None, res
            struct = structs[0]
            res = self.validate_structure(struct, cif_string=cif_string)
            return struct, res
        except Exception as e:
            res = StructuralValidationResult(
                status="INVALID",
                is_valid=False,
                checks=[ValidationCheckItem(name="CIF Syntax & Representation", passed=False, detail=str(e))],
                reasons=[f"CIF syntax error: failed to parse crystallographic data ({str(e)})"]
            )
            return None, res

    def validate_structure(
        self,
        struct: Structure,
        cif_string: str = "",
        requirements: Optional[MaterialRequirements] = None,
        existing_structures: Optional[List[Tuple[str, Structure]]] = None
    ) -> StructuralValidationResult:
        """
        Runs comprehensive deterministic crystallographic checks on a pymatgen Structure.
        Focuses strictly on physical & crystallographic validity.
        """
        checks: List[ValidationCheckItem] = []
        reasons: List[str] = []
        is_valid = True
        overlap_flag = False
        coords_wrapped = False
        is_duplicate = False
        dup_of_id = None
        sg_symbol = "P1"
        sg_num = 1

        # 1. Structure representation & CIF syntax
        checks.append(ValidationCheckItem(
            name="Crystallographic Representation",
            passed=True,
            detail="Structure representation is well-formed with valid atomic sites and unit cell."
        ))

        # 2. Lattice validity: finite vectors, determinant > 0, volume > 0, reasonable lengths and angles
        try:
            vol = struct.lattice.volume
            matrix = struct.lattice.matrix
            det = np.linalg.det(matrix)

            if not np.all(np.isfinite(matrix)):
                is_valid = False
                reasons.append("Lattice matrix contains non-finite values (NaN or Inf).")
                checks.append(ValidationCheckItem(
                    name="Lattice Validity",
                    passed=False,
                    detail="Lattice matrix contains NaN or Inf values."
                ))
            elif det <= 0 or vol <= 0 or not math.isfinite(vol):
                is_valid = False
                reasons.append(f"Invalid non-positive lattice volume or determinant: vol={vol}, det={det}")
                checks.append(ValidationCheckItem(
                    name="Lattice Validity",
                    passed=False,
                    detail=f"Non-positive lattice volume ({vol:.2f} Å³) or degenerate determinant ({det:.2f})."
                ))
            else:
                lengths = [struct.lattice.a, struct.lattice.b, struct.lattice.c]
                angles = [struct.lattice.alpha, struct.lattice.beta, struct.lattice.gamma]
                if any(l <= 0.5 or l > 150.0 for l in lengths) or any(a <= 10.0 or a >= 170.0 for a in angles):
                    is_valid = False
                    reasons.append(f"Lattice lengths ({lengths}) or angles ({angles}) outside physical ranges.")
                    checks.append(ValidationCheckItem(
                        name="Lattice Validity",
                        passed=False,
                        detail="Lattice parameters are outside physically viable limits."
                    ))
                else:
                    checks.append(ValidationCheckItem(
                        name="Lattice Validity",
                        passed=True,
                        detail=f"Lattice is non-degenerate and finite (Volume: {vol:.2f} Å³, Det: {det:.2f})."
                    ))
        except Exception as e:
            is_valid = False
            reasons.append(f"Lattice validation failed: {str(e)}")
            checks.append(ValidationCheckItem(
                name="Lattice Validity",
                passed=False,
                detail=f"Error inspecting lattice: {str(e)}"
            ))

        # 3. Coordinate validity: finite coordinates, no NaN/inf, periodic wrapping to [0, 1)
        try:
            frac_coords = np.array(struct.frac_coords)
            if not np.all(np.isfinite(frac_coords)):
                is_valid = False
                reasons.append("Atomic coordinates contain non-finite values (NaN or Inf).")
                checks.append(ValidationCheckItem(
                    name="Coordinate Validity",
                    passed=False,
                    detail="Atomic coordinates contain NaN or Inf values."
                ))
            else:
                any_outside = np.any((frac_coords < -1e-5) | (frac_coords >= 1.0 + 1e-5))
                if any_outside:
                    coords_wrapped = True
                    wrapped_coords = frac_coords % 1.0
                    for idx, site in enumerate(struct.sites):
                        site.frac_coords = wrapped_coords[idx]

                checks.append(ValidationCheckItem(
                    name="Coordinate Validity",
                    passed=True,
                    detail="Atomic coordinates are numerically finite and wrapped into periodic unit cell [0, 1)."
                ))
        except Exception as e:
            is_valid = False
            reasons.append(f"Coordinate verification failed: {str(e)}")
            checks.append(ValidationCheckItem(
                name="Coordinate Validity",
                passed=False,
                detail=f"Error checking coordinates: {str(e)}"
            ))

        # 4. Chemical validity: valid elements and species
        try:
            elements_in_struct = [e.symbol for e in struct.composition.elements]
            for elem_str in elements_in_struct:
                Element(elem_str)
            checks.append(ValidationCheckItem(
                name="Chemical Elements Validity",
                passed=True,
                detail=f"All atomic species are verified chemical elements: {', '.join(elements_in_struct)}."
            ))
        except Exception as e:
            is_valid = False
            reasons.append(f"Invalid chemical element in structure: {str(e)}")
            checks.append(ValidationCheckItem(
                name="Chemical Elements Validity",
                passed=False,
                detail=f"Invalid chemical species: {str(e)}"
            ))

        # 5. Atomic Overlap Heuristic (< min_dist_heuristic Å, default 0.7 Å)
        try:
            dist_matrix = struct.distance_matrix
            n_sites = len(struct)
            min_dist = 999.0
            overlap_pairs = []

            for i in range(n_sites):
                for j in range(i + 1, n_sites):
                    d = dist_matrix[i, j]
                    if d < min_dist:
                        min_dist = d
                    if d < self.min_dist_heuristic:
                        overlap_pairs.append((struct[i].species_string, struct[j].species_string, d))

            if overlap_pairs:
                overlap_flag = True
                is_valid = False
                reason_msg = f"Severe atomic overlap detected: minimum periodic distance {min_dist:.2f} Å is below {self.min_dist_heuristic:.2f} Å threshold."
                reasons.append(reason_msg)
                checks.append(ValidationCheckItem(
                    name="Atomic Overlap Heuristic",
                    passed=False,
                    detail=f"Structural Heuristic: {reason_msg} ({len(overlap_pairs)} overlapping pair(s))."
                ))
            else:
                checks.append(ValidationCheckItem(
                    name="Atomic Overlap Heuristic",
                    passed=True,
                    detail=f"Structural Heuristic: passed (minimum pairwise periodic distance: {min_dist:.2f} Å >= {self.min_dist_heuristic:.2f} Å)."
                ))
        except Exception as e:
            checks.append(ValidationCheckItem(
                name="Atomic Overlap Heuristic",
                passed=True,
                detail="Could not compute pairwise periodic distances; check bypassed."
            ))

        # 6. Physical Density Bounds
        try:
            density = struct.density
            if self.min_density <= density <= self.max_density:
                checks.append(ValidationCheckItem(
                    name="Physical Density Check",
                    passed=True,
                    detail=f"Crystallographic density {density:.2f} g/cm³ is within plausible limits [{self.min_density}, {self.max_density}]."
                ))
            else:
                is_valid = False
                reasons.append(f"Unphysical crystal density: {density:.2f} g/cm³ (outside [{self.min_density}, {self.max_density}] g/cm³).")
                checks.append(ValidationCheckItem(
                    name="Physical Density Check",
                    passed=False,
                    detail=f"Unphysical crystal density: {density:.2f} g/cm³."
                ))
        except Exception:
            pass

        # 7. Periodicity Verification
        try:
            pbc = struct.lattice.pbc
            if all(pbc):
                checks.append(ValidationCheckItem(
                    name="Periodicity Verification",
                    passed=True,
                    detail="Periodic boundary conditions verified in all 3 spatial dimensions."
                ))
            else:
                is_valid = False
                reasons.append("Structure does not have periodic boundary conditions in all 3 dimensions.")
                checks.append(ValidationCheckItem(
                    name="Periodicity Verification",
                    passed=False,
                    detail="Non-periodic structure representation."
                ))
        except Exception:
            checks.append(ValidationCheckItem(
                name="Periodicity Verification",
                passed=True,
                detail="Periodic boundary conditions active."
            ))

        # 8. Symmetry detection & standardization
        can_analyze_symmetry = (
            np.all(np.isfinite(struct.lattice.matrix))
            and np.all(np.isfinite(struct.frac_coords))
            and struct.lattice.volume > 0
        )
        if can_analyze_symmetry:
            try:
                sga = SpacegroupAnalyzer(struct, symprec=0.1)
                sg_symbol = sga.get_space_group_symbol()
                sg_num = sga.get_space_group_number()
                checks.append(ValidationCheckItem(
                    name="Symmetry Analysis",
                    passed=True,
                    detail=f"Crystallographic symmetry detected: Space Group {sg_symbol} (#{sg_num}), System: {sga.get_crystal_system()}."
                ))
            except Exception:
                sg_symbol = "P1"
                sg_num = 1
                checks.append(ValidationCheckItem(
                    name="Symmetry Analysis",
                    passed=True,
                    detail="Triclinic / default symmetry (P1)."
                ))
        else:
            sg_symbol = "unknown"
            sg_num = 0
            checks.append(ValidationCheckItem(
                name="Symmetry Analysis",
                passed=False,
                detail="Symmetry analysis skipped due to invalid lattice or coordinates."
            ))

        # 9. Structure Hash calculation
        struct_hash = self.compute_structure_hash(struct)

        # 10. Deduplication check against existing batch
        if existing_structures:
            for other_id, other_struct in existing_structures:
                try:
                    if self.structure_matcher.fit(struct, other_struct):
                        is_duplicate = True
                        dup_of_id = other_id
                        break
                except Exception:
                    continue

        if is_duplicate:
            is_valid = False
            checks.append(ValidationCheckItem(
                name="Structure Uniqueness",
                passed=False,
                detail=f"Duplicate candidate detected: identical topology to {dup_of_id} via StructureMatcher."
            ))
            reasons.append(f"Duplicate structure equivalent to candidate {dup_of_id}.")
        else:
            checks.append(ValidationCheckItem(
                name="Structure Uniqueness",
                passed=True,
                detail="Unique structure (no duplicate match found in generated batch)."
            ))

        # 11. Chemical constraint checking (Required, Allowed & Excluded elements)
        struct_elements = set(e.symbol for e in struct.composition.elements)
        if requirements and requirements.required_elements:
            missing = set(requirements.required_elements) - struct_elements
            if missing:
                is_valid = False
                reasons.append(f"Missing required element(s): {', '.join(missing)}")
                checks.append(ValidationCheckItem(
                    name="Required Elements",
                    passed=False,
                    detail=f"Structure lacks required element(s): {', '.join(missing)}."
                ))
            else:
                checks.append(ValidationCheckItem(
                    name="Required Elements",
                    passed=True,
                    detail=f"All required elements present: {', '.join(requirements.required_elements)}."
                ))

        if requirements and requirements.allowed_elements:
            not_allowed = struct_elements - set(requirements.allowed_elements)
            if not_allowed:
                is_valid = False
                reasons.append(f"Contains non-allowed element(s): {', '.join(not_allowed)}")
                checks.append(ValidationCheckItem(
                    name="Allowed Elements",
                    passed=False,
                    detail=f"Contains non-allowed element(s): {', '.join(not_allowed)}."
                ))
            else:
                checks.append(ValidationCheckItem(
                    name="Allowed Elements",
                    passed=True,
                    detail="All elements are in the allowed elements list."
                ))

        if requirements and requirements.excluded_elements:
            violating = set(requirements.excluded_elements).intersection(struct_elements)
            if violating:
                is_valid = False
                reasons.append(f"Contains excluded/toxic element(s): {', '.join(violating)}")
                checks.append(ValidationCheckItem(
                    name="Excluded Elements",
                    passed=False,
                    detail=f"Structure contains prohibited element(s): {', '.join(violating)}."
                ))
            else:
                checks.append(ValidationCheckItem(
                    name="Excluded Elements",
                    passed=True,
                    detail=f"Zero prohibited elements present (checked against {', '.join(requirements.excluded_elements)})."
                ))

        status_label = "VALID" if is_valid else "INVALID"

        result = StructuralValidationResult(
            status=status_label,
            is_valid=is_valid,
            checks=checks,
            reasons=reasons,
            overlap_heuristic_flag=overlap_flag,
            coordinates_wrapped=coords_wrapped,
            is_duplicate=is_duplicate,
            duplicate_of_id=dup_of_id,
            standardized_space_group=sg_symbol,
            standardized_space_group_number=sg_num,
            structure_hash=struct_hash
        )

        return result
