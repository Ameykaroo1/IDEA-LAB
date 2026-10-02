import sqlite3
import zipfile
import json
import time

def main():
    db_path = "data/reference_catalog.db"
    zip_path = "data/jarvis_dft/jarvis_dft_3d.zip"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if column exists
    cur.execute("PRAGMA table_info(reference_materials)")
    cols = [col[1] for col in cur.fetchall()]
    if "site_elements_json" not in cols:
        print("Adding column site_elements_json to reference_materials...")
        cur.execute("ALTER TABLE reference_materials ADD COLUMN site_elements_json TEXT")
        conn.commit()
    else:
        print("Column site_elements_json already exists.")

    print(f"Reading JARVIS JSON from {zip_path}...")
    t0 = time.time()
    with zipfile.ZipFile(zip_path, "r") as zf:
        json_filenames = [name for name in zf.namelist() if name.endswith(".json")]
        if not json_filenames:
            raise FileNotFoundError("No JSON file found in JARVIS zip")
        with zf.open(json_filenames[0]) as f:
            data = json.load(f)
    print(f"Loaded {len(data)} JARVIS records in {time.time() - t0:.2f}s")

    print("Updating site_elements_json for JARVIS records...")
    t1 = time.time()
    batch = []
    updated_count = 0

    for item in data:
        jid = str(item.get("jid", "")).strip()
        atoms = item.get("atoms", {})
        if not jid or not isinstance(atoms, dict):
            continue
        site_elements = atoms.get("elements", [])
        if site_elements:
            batch.append((json.dumps(site_elements), jid))

        if len(batch) >= 10000:
            cur.executemany("UPDATE reference_materials SET site_elements_json = ? WHERE material_id = ?", batch)
            conn.commit()
            updated_count += len(batch)
            print(f"Updated {updated_count}/{len(data)} records...")
            batch = []

    if batch:
        cur.executemany("UPDATE reference_materials SET site_elements_json = ? WHERE material_id = ?", batch)
        conn.commit()
        updated_count += len(batch)

    print(f"Successfully updated {updated_count} JARVIS records in {time.time() - t1:.2f}s")

    # Verify a record
    cur.execute("SELECT material_id, formula, site_elements_json, coords_json, lattice_json FROM reference_materials WHERE dataset_source='JARVIS-DFT' LIMIT 1")
    row = cur.fetchone()
    print("Verified Row:")
    print("ID:", row[0], "Formula:", row[1])
    site_elems = json.loads(row[2])
    coords = json.loads(row[3])
    lat = json.loads(row[4])
    print(f"Site elements count: {len(site_elems)}, Coords count: {len(coords)}")
    assert len(site_elems) == len(coords), f"Mismatch: {len(site_elems)} != {len(coords)}"

    # Test Structure creation
    from pymatgen.core import Structure, Lattice
    struct = Structure(Lattice(lat), site_elems, coords, coords_are_cartesian=True)
    print("Successfully built Pymatgen Structure for JARVIS:", struct.formula, "Volume:", round(struct.lattice.volume, 2))

    conn.close()

if __name__ == "__main__":
    main()
