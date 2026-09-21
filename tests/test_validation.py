"""
Structural Validation Tests for CRYSTAL-X.
Covers:
- 5 Valid structure tests
- 5 Invalid structure tests
- Fractional coordinate wrapping (wrapping outside [0, 1) into unit cell)
- Obvious atom-overlap heuristic test
- Duplicate detection via StructureMatcher
"""

import pytest
import numpy as np
from pymatgen.core import Structure, Lattice
from pymatgen.io.cif import CifWriter
from backend.services.validation_service import StructuralValidationService
from backend.models.schemas import MaterialRequirements


@pytest.fixture
def validator():
    return StructuralValidationService(min_atomic_distance_heuristic=0.7)


# ==========================================
# 5 VALID STRUCTURE TESTS
# ==========================================

def test_valid_1_silicon_diamond(validator):
    lat = Lattice.cubic(5.43)
    s = Structure(lat, ["Si"] * 8, [
        [0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5],
        [0.25, 0.25, 0.25], [0.75, 0.75, 0.25], [0.75, 0.25, 0.75], [0.25, 0.75, 0.75]
    ])
    cif = str(CifWriter(s))
    res = validator.validate_structure(s, cif)
    assert res.is_valid is True
    assert res.status == "VALID"


def test_valid_2_licoo2_layered(validator):
    lat = Lattice.hexagonal(2.82, 14.05)
    s = Structure(lat, ["Li", "Co", "O", "O"], [
        [0, 0, 0.5],
        [0, 0, 0],
        [0, 0, 0.24],
        [0, 0, 0.76]
    ])
    cif = str(CifWriter(s))
    res = validator.validate_structure(s, cif)
    assert res.is_valid is True
    assert res.status == "VALID"


def test_valid_3_lifepo4_olivine(validator):
    lat = Lattice.orthorhombic(10.33, 6.01, 4.69)
    s = Structure(lat, ["Li", "Fe", "P", "O", "O", "O", "O"], [
        [0, 0, 0],
        [0.28, 0.25, 0.97],
        [0.09, 0.25, 0.42],
        [0.10, 0.25, 0.74],
        [0.45, 0.25, 0.21],
        [0.17, 0.05, 0.28],
        [0.17, 0.45, 0.28]
    ])
    cif = str(CifWriter(s))
    res = validator.validate_structure(s, cif)
    assert res.is_valid is True


def test_valid_4_solid_electrolyte_thiophosphate(validator):
    lat = Lattice.tetragonal(8.72, 12.63)
    s = Structure(lat, ["Li", "Li", "Ge", "P", "S", "S"], [
        [0.25, 0.25, 0.18],
        [0.25, 0.25, 0.00],
        [0.0, 0.0, 0.0],
        [0.0, 0.5, 0.25],
        [0.18, 0.18, 0.41],
        [0.69, 0.19, 0.14]
    ])
    cif = str(CifWriter(s))
    res = validator.validate_structure(s, cif)
    assert res.is_valid is True


def test_valid_5_sodium_vanadium_phosphate(validator):
    lat = Lattice.hexagonal(8.73, 21.80)
    s = Structure(lat, ["Na", "Na", "V", "P", "O", "O"], [
        [0, 0, 0],
        [0.64, 0, 0.25],
        [0, 0, 0.15],
        [0.29, 0, 0.25],
        [0.18, 0.17, 0.09],
        [0.19, 0.99, 0.19]
    ])
    cif = str(CifWriter(s))
    res = validator.validate_structure(s, cif)
    assert res.is_valid is True


# ==========================================
# 5 INVALID STRUCTURE TESTS
# ==========================================

def test_invalid_1_overlapping_atoms(validator):
    lat = Lattice.cubic(5.0)
    # Two atoms spaced by only 0.2 Å (well below the 0.7 Å heuristic threshold)
    s = Structure(lat, ["Si", "Si"], [
        [0.0, 0.0, 0.0],
        [0.04, 0.0, 0.0]  # 0.04 * 5.0 = 0.20 Å
    ])
    cif = str(CifWriter(s))
    res = validator.validate_structure(s, cif)
    assert res.is_valid is False
    assert res.overlap_heuristic_flag is True
    assert any("overlap" in r.lower() for r in res.reasons)


def test_invalid_2_missing_required_element(validator):
    lat = Lattice.cubic(4.0)
    s = Structure(lat, ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    cif = str(CifWriter(s))
    reqs = MaterialRequirements(required_elements=["Si"])
    res = validator.validate_structure(s, cif, requirements=reqs)
    assert res.is_valid is False
    assert any("Missing required element" in r for r in res.reasons)


def test_invalid_3_contains_excluded_element(validator):
    lat = Lattice.cubic(4.0)
    s = Structure(lat, ["Pb", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    cif = str(CifWriter(s))
    reqs = MaterialRequirements(excluded_elements=["Pb", "Cd", "Hg"])
    res = validator.validate_structure(s, cif, requirements=reqs)
    assert res.is_valid is False
    assert any("excluded/toxic element" in r for r in res.reasons)


def test_invalid_4_cif_syntax_malformed(validator):
    malformed_cif = "data_broken\n_cell_length_a NOT_A_NUMBER\nloop_\n_atom_site_fract_x\n"
    struct, res = validator.parse_and_validate_cif_string(malformed_cif)
    assert struct is None
    assert res.is_valid is False
    assert any("error" in r.lower() or "failed" in r.lower() for r in res.reasons)


def test_invalid_5_allowed_elements_violation(validator):
    lat = Lattice.cubic(4.0)
    s = Structure(lat, ["Fe", "O"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    cif = str(CifWriter(s))
    reqs = MaterialRequirements(allowed_elements=["Si", "O"])  # Fe is not allowed
    res = validator.validate_structure(s, cif, requirements=reqs)
    assert res.is_valid is False
    assert any("non-allowed" in r for r in res.reasons)


# ==========================================
# COORDINATE WRAPPING CORRECTION TEST
# ==========================================

def test_fractional_coordinates_wrapping(validator):
    lat = Lattice.cubic(5.0)
    # Coordinate outside [0, 1), e.g. 1.25 and -0.25, mathematically equivalent to periodic lattice
    s = Structure(lat, ["Si", "Si"], [
        [1.25, 0.5, 0.5],
        [-0.25, 0.0, 0.0]
    ])
    cif = str(CifWriter(s))
    res = validator.validate_structure(s, cif)
    # MUST NOT be rejected solely because coordinates were outside [0, 1)
    assert res.is_valid is True
    assert res.coordinates_wrapped is True


# ==========================================
# DUPLICATE DETECTION TEST
# ==========================================

def test_duplicate_detection(validator):
    lat = Lattice.cubic(5.43)
    s1 = Structure(lat, ["Si"] * 8, [
        [0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5],
        [0.25, 0.25, 0.25], [0.75, 0.75, 0.25], [0.75, 0.25, 0.75], [0.25, 0.75, 0.75]
    ])
    # Exact translated duplicate
    s2 = s1.copy()
    s2.translate_sites([0, 1, 2, 3, 4, 5, 6, 7], [0.5, 0.5, 0.5])
    
    existing = [("C-001", s1)]
    cif2 = str(CifWriter(s2))
    res = validator.validate_structure(s2, cif2, existing_structures=existing)
    assert res.is_duplicate is True
    assert res.duplicate_of_id == "C-001"
    assert res.is_valid is False  # Rejected as duplicate candidate
