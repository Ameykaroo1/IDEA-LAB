import sqlite3
import json
from pymatgen.core import Structure, Lattice

conn = sqlite3.connect('data/reference_catalog.db')
cur = conn.cursor()

# 1. Test MP-20
cur.execute("SELECT material_id, cif FROM reference_materials WHERE dataset_source='MP-20' LIMIT 1")
row = cur.fetchone()
print("MP-20 ID:", row[0])
struct_mp = Structure.from_str(row[1], fmt="cif")
print("MP-20 Structure:", struct_mp.composition.reduced_formula, "Volume:", round(struct_mp.lattice.volume, 2), "Sites:", len(struct_mp))

# 2. Check JARVIS
cur.execute("SELECT material_id, formula, elements_json, lattice_json, coords_json FROM reference_materials WHERE dataset_source='JARVIS-DFT' LIMIT 1")
row_j = cur.fetchone()
print("JARVIS ID:", row_j[0], "Formula:", row_j[1])
print("JARVIS elements_json:", row_j[2])
print("JARVIS lattice len:", len(json.loads(row_j[3])))
print("JARVIS coords len:", len(json.loads(row_j[4])))
conn.close()
