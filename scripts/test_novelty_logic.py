import sqlite3
import json
import time
from pymatgen.core import Structure, Lattice
from pymatgen.analysis.structure_matcher import StructureMatcher

matcher = StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5.0, primitive_cell=True, scale=True)
conn = sqlite3.connect("data/reference_catalog.db")
cur = conn.cursor()

# 1. Test duplicate match against an MP-20 structure
print("--- TEST 1: MP-20 self-match ---")
cur.execute("SELECT material_id, formula, chemical_system, cif FROM reference_materials WHERE dataset_source='MP-20' AND chemical_system='Si' LIMIT 1")
row = cur.fetchone()
mp_id, mp_formula, chem_sys, cif = row
mp_struct = Structure.from_str(cif, fmt="cif")

t0 = time.time()
cur.execute("SELECT material_id, dataset_source, formula, cif, lattice_json, coords_json, site_elements_json FROM reference_materials WHERE chemical_system = ?", (chem_sys,))
candidates = cur.fetchall()
query_time = time.time() - t0

matched = None
t1 = time.time()
for r in candidates:
    r_id, r_source, r_form, r_cif, r_lat, r_coords, r_sites = r
    if r_source == "MP-20" and r_cif:
        ref_st = Structure.from_str(r_cif, fmt="cif")
    elif r_source == "JARVIS-DFT" and r_lat and r_coords and r_sites:
        ref_st = Structure(Lattice(json.loads(r_lat)), json.loads(r_sites), json.loads(r_coords), coords_are_cartesian=True)
    else:
        continue
    if matcher.fit(mp_struct, ref_st):
        matched = (r_id, r_source, r_form)
        break
match_time = time.time() - t1

print(f"Query returned {len(candidates)} candidates in {query_time*1000:.2f}ms")
print(f"Structure matching completed in {match_time*1000:.2f}ms")
print(f"Matched: {matched}")
assert matched is not None and matched[0] == mp_id, f"Expected {mp_id}, got {matched}"

# 2. Test duplicate match against a JARVIS structure
print("\n--- TEST 2: JARVIS-DFT self-match ---")
cur.execute("SELECT material_id, formula, chemical_system, lattice_json, coords_json, site_elements_json FROM reference_materials WHERE dataset_source='JARVIS-DFT' LIMIT 1")
row_j = cur.fetchone()
j_id, j_formula, j_chem_sys, j_lat, j_coords, j_sites = row_j
jarvis_struct = Structure(Lattice(json.loads(j_lat)), json.loads(j_sites), json.loads(j_coords), coords_are_cartesian=True)

t0 = time.time()
cur.execute("SELECT material_id, dataset_source, formula, cif, lattice_json, coords_json, site_elements_json FROM reference_materials WHERE chemical_system = ?", (j_chem_sys,))
candidates_j = cur.fetchall()
query_time_j = time.time() - t0

matched_j = None
t1 = time.time()
for r in candidates_j:
    r_id, r_source, r_form, r_cif, r_lat, r_coords, r_sites = r
    if r_source == "MP-20" and r_cif:
        ref_st = Structure.from_str(r_cif, fmt="cif")
    elif r_source == "JARVIS-DFT" and r_lat and r_coords and r_sites:
        ref_st = Structure(Lattice(json.loads(r_lat)), json.loads(r_sites), json.loads(r_coords), coords_are_cartesian=True)
    else:
        continue
    if matcher.fit(jarvis_struct, ref_st):
        matched_j = (r_id, r_source, r_form)
        break
match_time_j = time.time() - t1

print(f"JARVIS Query returned {len(candidates_j)} candidates in {query_time_j*1000:.2f}ms")
print(f"JARVIS Structure matching completed in {match_time_j*1000:.2f}ms")
print(f"Matched: {matched_j}")
assert matched_j is not None, "Failed to match JARVIS structure"

print("\nALL NOVELTY LOGIC TESTS PASSED!")
conn.close()
