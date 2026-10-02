"""
Ingestion & Harmonization Pipeline for Full MP-20 and JARVIS-DFT Datasets.
Downloads, validates, normalizes, and indexes:
1. MP-20 (Materials Project 2020 Benchmark): 45,229 crystal structures
2. JARVIS-DFT 3D (NIST): ~93,902 crystal structures
Creates a persistent, multi-stage searchable SQLite catalog and ingestion audit report.
"""

import os
import io
import sys
import json
import zipfile
import sqlite3
import datetime
import urllib.request
import ast
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MP20_DIR = os.path.join(DATA_DIR, "mp20")
JARVIS_DIR = os.path.join(DATA_DIR, "jarvis_dft")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
DB_PATH = os.path.join(DATA_DIR, "reference_catalog.db")
REPORT_PATH = os.path.join(PROCESSED_DIR, "dataset_ingestion_report.json")

MP20_URL = "https://media.githubusercontent.com/media/microsoft/mattergen/main/data-release/mp-20/mp_20.zip"
JARVIS_URL = "https://ndownloader.figshare.com/files/64391379"

os.makedirs(MP20_DIR, exist_ok=True)
os.makedirs(JARVIS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def download_file(url: str, dest_path: str, label: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000000:
        print(f"[{label}] Existing archive found ({os.path.getsize(dest_path)} bytes). Skipping download.")
        return dest_path

    print(f"[{label}] Downloading from {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "CRYSTAL-X-Ingestion/2.0"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1 MB chunks
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                sys.stdout.write(f"\r[{label}] Progress: {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)")
                sys.stdout.flush()
        print(f"\n[{label}] Download complete: {os.path.getsize(dest_path)} bytes.")
    return dest_path


def init_database(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reference_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id TEXT NOT NULL UNIQUE,
        dataset_source TEXT NOT NULL,
        dataset_split TEXT,
        formula TEXT,
        reduced_formula TEXT,
        chemical_system TEXT,
        elements_json TEXT,
        element_count INTEGER,
        crystal_system TEXT,
        space_group TEXT,
        space_group_number INTEGER,
        formation_energy_per_atom REAL,
        energy_above_hull REAL,
        band_gap REAL,
        density REAL,
        nsites INTEGER,
        cif TEXT,
        lattice_json TEXT,
        coords_json TEXT,
        properties_json TEXT,
        structure_available INTEGER NOT NULL DEFAULT 1
    );
    """)

    # Indices for high performance queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_chemical_system ON reference_materials(chemical_system);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_reduced_formula ON reference_materials(reduced_formula);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_formula ON reference_materials(formula);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_dataset_source ON reference_materials(dataset_source);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_ehull ON reference_materials(energy_above_hull);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_band_gap ON reference_materials(band_gap);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_formation_energy ON reference_materials(formation_energy_per_atom);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_space_group ON reference_materials(space_group_number);")
    conn.commit()
    return conn


def parse_mp20(zip_path: str, conn: sqlite3.Connection) -> Dict[str, Any]:
    print("\n=== INGESTING MP-20 DATASET ===")
    stats = {
        "dataset": "MP-20",
        "expected_records": 45229,
        "total_records": 0,
        "train_records": 0,
        "val_records": 0,
        "test_records": 0,
        "valid_structures": 0,
        "valid_lattice": 0,
        "valid_coordinates": 0,
        "duplicate_ids": 0,
        "invalid_records": 0,
        "unique_formulas": 0,
        "unique_elements": set(),
        "invalid_log": []
    }

    seen_ids = set()
    unique_formulas = set()
    records_to_insert = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        splits = [
            ("train", "mp_20/train.csv", 27136),
            ("val", "mp_20/val.csv", 9047),
            ("test", "mp_20/test.csv", 9046)
        ]

        for split_name, csv_filename, expected_split_count in splits:
            print(f"[MP-20] Reading {split_name} split from {csv_filename} (expected {expected_split_count})...")
            with zf.open(csv_filename) as f:
                df = pd.read_csv(f)
                split_len = len(df)
                if split_name == "train":
                    stats["train_records"] = split_len
                elif split_name == "val":
                    stats["val_records"] = split_len
                elif split_name == "test":
                    stats["test_records"] = split_len

                for _, row in df.iterrows():
                    stats["total_records"] += 1
                    mat_id = str(row.get("material_id", "")).strip()

                    if not mat_id or mat_id in seen_ids:
                        stats["duplicate_ids"] += 1
                        stats["invalid_records"] += 1
                        stats["invalid_log"].append(f"Duplicate or empty ID: {mat_id}")
                        continue
                    seen_ids.add(mat_id)

                    formula = str(row.get("pretty_formula", "")).strip()
                    unique_formulas.add(formula)

                    # Elements parsing
                    raw_elems = row.get("elements", "[]")
                    try:
                        elems = ast.literal_eval(raw_elems) if isinstance(raw_elems, str) else list(raw_elems)
                    except Exception:
                        elems = [e.strip() for e in str(raw_elems).replace("[", "").replace("]", "").replace("'", "").split(",") if e.strip()]
                    
                    for el in elems:
                        stats["unique_elements"].add(el)
                    chem_sys = "-".join(sorted(elems))

                    cif_str = str(row.get("cif", "")).strip()
                    has_struct = bool(cif_str and "_cell_length_" in cif_str and "_atom_site_" in cif_str)
                    
                    if has_struct:
                        stats["valid_structures"] += 1
                        stats["valid_lattice"] += 1
                        stats["valid_coordinates"] += 1
                    else:
                        stats["invalid_records"] += 1
                        stats["invalid_log"].append(f"Material {mat_id} has invalid/empty CIF")

                    # Numerical properties
                    def to_float(val):
                        try:
                            if pd.isna(val): return None
                            return float(val)
                        except (ValueError, TypeError):
                            return None

                    def to_int(val):
                        try:
                            if pd.isna(val): return None
                            return int(float(val))
                        except (ValueError, TypeError):
                            return None

                    form_energy = to_float(row.get("formation_energy_per_atom"))
                    ehull = to_float(row.get("e_above_hull"))
                    bg = to_float(row.get("dft_band_gap"))
                    spg_num = to_int(row.get("spacegroup_number"))

                    props = {
                        "azure_bulk_modulus": to_float(row.get("azure_bulk_modulus")),
                        "dft_bulk_modulus": to_float(row.get("dft_bulk_modulus")),
                        "dft_poisson_ratio": to_float(row.get("dft_poisson_ratio")),
                        "azure_band_gap": to_float(row.get("azure_band_gap")),
                        "larsen_score_2d": to_float(row.get("larsen_score_2d")),
                        "Si_100_mismatch": to_float(row.get("Si_100_mismatch")),
                        "source_split": split_name
                    }

                    records_to_insert.append((
                        mat_id,
                        "MP-20",
                        split_name,
                        formula,
                        formula,  # reduced formula approx
                        chem_sys,
                        json.dumps(elems),
                        len(elems),
                        None,     # crystal system string can be derived from spg_num
                        f"SpaceGroup #{spg_num}" if spg_num else None,
                        spg_num,
                        form_energy,
                        ehull,
                        bg,
                        None,     # density
                        None,     # nsites
                        cif_str if has_struct else None,
                        None,     # lattice_json
                        None,     # coords_json
                        json.dumps(props),
                        1 if has_struct else 0
                    ))

                    if len(records_to_insert) >= 5000:
                        cur = conn.cursor()
                        cur.executemany("""
                        INSERT OR REPLACE INTO reference_materials (
                            material_id, dataset_source, dataset_split, formula, reduced_formula,
                            chemical_system, elements_json, element_count, crystal_system, space_group,
                            space_group_number, formation_energy_per_atom, energy_above_hull, band_gap,
                            density, nsites, cif, lattice_json, coords_json, properties_json, structure_available
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, records_to_insert)
                        conn.commit()
                        records_to_insert = []
                        sys.stdout.write(f"\r[MP-20] Indexed {stats['total_records']}/{stats['expected_records']} records...")
                        sys.stdout.flush()

        if records_to_insert:
            cur = conn.cursor()
            cur.executemany("""
            INSERT OR REPLACE INTO reference_materials (
                material_id, dataset_source, dataset_split, formula, reduced_formula,
                chemical_system, elements_json, element_count, crystal_system, space_group,
                space_group_number, formation_energy_per_atom, energy_above_hull, band_gap,
                density, nsites, cif, lattice_json, coords_json, properties_json, structure_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records_to_insert)
            conn.commit()

    stats["unique_formulas"] = len(unique_formulas)
    stats["unique_elements"] = sorted(list(stats["unique_elements"]))
    print(f"\n[MP-20] Ingestion finished. Loaded: {stats['total_records']}, Valid structures: {stats['valid_structures']}, Duplicates: {stats['duplicate_ids']}")
    return stats


def parse_jarvis(zip_path: str, conn: sqlite3.Connection) -> Dict[str, Any]:
    print("\n=== INGESTING JARVIS-DFT 3D DATASET ===")
    stats = {
        "dataset": "JARVIS-DFT",
        "expected_records": 93902,
        "total_records": 0,
        "valid_structures": 0,
        "valid_lattice": 0,
        "valid_coordinates": 0,
        "duplicate_ids": 0,
        "invalid_records": 0,
        "unique_formulas": 0,
        "unique_elements": set(),
        "invalid_log": []
    }

    seen_ids = set()
    unique_formulas = set()
    records_to_insert = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        json_filenames = [name for name in zf.namelist() if name.endswith(".json")]
        if not json_filenames:
            raise FileNotFoundError("No JSON file found in JARVIS zip archive")
        json_filename = json_filenames[0]
        print(f"[JARVIS-DFT] Reading {json_filename} from zip...")

        with zf.open(json_filename) as f:
            data = json.load(f)
            stats["total_records"] = len(data)
            print(f"[JARVIS-DFT] Found {len(data)} records in archive.")

            for idx, entry in enumerate(data):
                mat_id = str(entry.get("jid", "")).strip()
                if not mat_id or mat_id in seen_ids:
                    stats["duplicate_ids"] += 1
                    stats["invalid_records"] += 1
                    continue
                seen_ids.add(mat_id)

                formula = str(entry.get("formula", "")).strip()
                unique_formulas.add(formula)

                atoms = entry.get("atoms", {})
                has_atoms = isinstance(atoms, dict) and "lattice_mat" in atoms and "coords" in atoms and "elements" in atoms
                
                elems = atoms.get("elements", []) if has_atoms else []
                if not elems and "elements" in entry:
                    elems = entry["elements"]
                
                # Deduplicate elements preserving order
                clean_elems = []
                for el in elems:
                    if el not in clean_elems:
                        clean_elems.append(el)
                    stats["unique_elements"].add(el)
                chem_sys = "-".join(sorted(clean_elems))

                # Structure validity
                has_lattice = False
                has_coords = False
                lattice_mat = atoms.get("lattice_mat") if has_atoms else None
                coords = atoms.get("coords") if has_atoms else None

                if lattice_mat and len(lattice_mat) == 3 and all(len(row) == 3 for row in lattice_mat):
                    has_lattice = True
                    stats["valid_lattice"] += 1

                if coords and len(coords) > 0 and all(len(c) == 3 for c in coords):
                    has_coords = True
                    stats["valid_coordinates"] += 1

                is_valid = has_lattice and has_coords
                if is_valid:
                    stats["valid_structures"] += 1
                else:
                    stats["invalid_records"] += 1
                    stats["invalid_log"].append(f"JARVIS {mat_id} missing lattice or coordinates")

                def to_float(val):
                    try:
                        if val is None or val == "na" or val == "NaN": return None
                        return float(val)
                    except (ValueError, TypeError):
                        return None

                def to_int(val):
                    try:
                        if val is None or val == "na": return None
                        return int(val)
                    except (ValueError, TypeError):
                        return None

                form_energy = to_float(entry.get("formation_energy_peratom"))
                ehull = to_float(entry.get("ehull"))
                bg = to_float(entry.get("optb88vdw_bandgap"))
                if bg is None:
                    bg = to_float(entry.get("mbj_bandgap"))
                spg_num = to_int(entry.get("spg_number"))
                spg_sym = entry.get("spg_symbol") or entry.get("spg")
                crys_sys = entry.get("crys")
                density = to_float(entry.get("density"))
                nat = to_int(entry.get("nat"))

                # Keep all rich properties
                props = {
                    "bulk_modulus_kv": to_float(entry.get("bulk_modulus_kv")),
                    "shear_modulus_gv": to_float(entry.get("shear_modulus_gv")),
                    "mbj_bandgap": to_float(entry.get("mbj_bandgap")),
                    "hse_gap": to_float(entry.get("hse_gap")),
                    "slme": to_float(entry.get("slme")),
                    "exfoliation_energy": to_float(entry.get("exfoliation_energy")),
                    "encut": to_float(entry.get("encut")),
                    "optb88vdw_total_energy": to_float(entry.get("optb88vdw_total_energy")),
                    "dimensionality": entry.get("dimensionality")
                }

                records_to_insert.append((
                    mat_id,
                    "JARVIS-DFT",
                    "reference",
                    formula,
                    formula,
                    chem_sys,
                    json.dumps(clean_elems),
                    len(clean_elems),
                    crys_sys,
                    spg_sym,
                    spg_num,
                    form_energy,
                    ehull,
                    bg,
                    density,
                    nat,
                    None,  # CIF generated on demand or stored as atoms_json
                    json.dumps(lattice_mat) if has_lattice else None,
                    json.dumps(coords) if has_coords else None,
                    json.dumps(props),
                    1 if is_valid else 0
                ))

                if len(records_to_insert) >= 5000:
                    cur = conn.cursor()
                    cur.executemany("""
                    INSERT OR REPLACE INTO reference_materials (
                        material_id, dataset_source, dataset_split, formula, reduced_formula,
                        chemical_system, elements_json, element_count, crystal_system, space_group,
                        space_group_number, formation_energy_per_atom, energy_above_hull, band_gap,
                        density, nsites, cif, lattice_json, coords_json, properties_json, structure_available
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, records_to_insert)
                    conn.commit()
                    records_to_insert = []
                    sys.stdout.write(f"\r[JARVIS-DFT] Indexed {idx + 1}/{stats['total_records']} records...")
                    sys.stdout.flush()

        if records_to_insert:
            cur = conn.cursor()
            cur.executemany("""
            INSERT OR REPLACE INTO reference_materials (
                material_id, dataset_source, dataset_split, formula, reduced_formula,
                chemical_system, elements_json, element_count, crystal_system, space_group,
                space_group_number, formation_energy_per_atom, energy_above_hull, band_gap,
                density, nsites, cif, lattice_json, coords_json, properties_json, structure_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records_to_insert)
            conn.commit()

    stats["unique_formulas"] = len(unique_formulas)
    stats["unique_elements"] = sorted(list(stats["unique_elements"]))
    print(f"\n[JARVIS-DFT] Ingestion finished. Loaded: {stats['total_records']}, Valid structures: {stats['valid_structures']}, Duplicates: {stats['duplicate_ids']}")
    return stats


def run_full_ingestion():
    start_time = datetime.datetime.now(datetime.timezone.utc)
    print("==================================================")
    print("CRYSTAL-X FULL DATASET INGESTION & HARMONIZATION")
    print(f"Timestamp: {start_time.isoformat()}")
    print("==================================================")

    # 1. Download archives
    mp20_zip = os.path.join(MP20_DIR, "mp_20.zip")
    jarvis_zip = os.path.join(JARVIS_DIR, "jarvis_dft_3d.zip")

    download_file(MP20_URL, mp20_zip, "MP-20")
    download_file(JARVIS_URL, jarvis_zip, "JARVIS-DFT")

    # 2. Initialize Database
    conn = init_database(DB_PATH)

    # 3. Parse and Index MP-20
    mp20_stats = parse_mp20(mp20_zip, conn)

    # 4. Parse and Index JARVIS-DFT
    jarvis_stats = parse_jarvis(jarvis_zip, conn)

    # 5. Database Statistics & Cross-Dataset Audit
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM reference_materials;")
    total_db_records = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM reference_materials WHERE structure_available = 1;")
    total_with_structures = cur.fetchone()[0]

    cur.execute("SELECT dataset_source, COUNT(*) FROM reference_materials GROUP BY dataset_source;")
    counts_by_source = dict(cur.fetchall())

    cur.execute("SELECT COUNT(DISTINCT chemical_system) FROM reference_materials;")
    unique_chem_systems = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT reduced_formula) FROM reference_materials;")
    unique_formulas_total = cur.fetchone()[0]

    conn.close()

    end_time = datetime.datetime.now(datetime.timezone.utc)
    duration_sec = (end_time - start_time).total_seconds()

    report = {
        "title": "CRYSTAL-X Full Reference Dataset Ingestion & Validation Report",
        "ingested_at": end_time.isoformat(),
        "duration_seconds": round(duration_sec, 2),
        "database_file": os.path.relpath(DB_PATH, BASE_DIR),
        "database_size_bytes": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
        "total_records_indexed": total_db_records,
        "total_valid_structures": total_with_structures,
        "unique_chemical_systems": unique_chem_systems,
        "unique_formulas": unique_formulas_total,
        "counts_by_source": counts_by_source,
        "mp20": {
            "source": MP20_URL,
            "status": "FULL",
            "expected_records": mp20_stats["expected_records"],
            "total_loaded": mp20_stats["total_records"],
            "train_records": mp20_stats["train_records"],
            "val_records": mp20_stats["val_records"],
            "test_records": mp20_stats["test_records"],
            "valid_structures": mp20_stats["valid_structures"],
            "valid_lattice": mp20_stats["valid_lattice"],
            "valid_coordinates": mp20_stats["valid_coordinates"],
            "duplicate_ids": mp20_stats["duplicate_ids"],
            "invalid_records": mp20_stats["invalid_records"],
            "unique_formulas": mp20_stats["unique_formulas"],
            "unique_elements_count": len(mp20_stats["unique_elements"])
        },
        "jarvis_dft": {
            "source": JARVIS_URL,
            "status": "FULL",
            "expected_records": jarvis_stats["expected_records"],
            "total_loaded": jarvis_stats["total_records"],
            "valid_structures": jarvis_stats["valid_structures"],
            "valid_lattice": jarvis_stats["valid_lattice"],
            "valid_coordinates": jarvis_stats["valid_coordinates"],
            "duplicate_ids": jarvis_stats["duplicate_ids"],
            "invalid_records": jarvis_stats["invalid_records"],
            "unique_formulas": jarvis_stats["unique_formulas"],
            "unique_elements_count": len(jarvis_stats["unique_elements"])
        }
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n==================================================")
    print("INGESTION SUMMARY")
    print(f"Total Database Records: {total_db_records:,}")
    print(f"Total Valid Structures: {total_with_structures:,}")
    print(f"MP-20 Records: {counts_by_source.get('MP-20', 0):,}")
    print(f"JARVIS-DFT Records: {counts_by_source.get('JARVIS-DFT', 0):,}")
    print(f"Unique Chemical Systems: {unique_chem_systems:,}")
    print(f"Unique Formulas: {unique_formulas_total:,}")
    print(f"Database Size: {os.path.getsize(DB_PATH) / (1024*1024):.1f} MB")
    print(f"Report written to: {os.path.relpath(REPORT_PATH, BASE_DIR)}")
    print("==================================================")


if __name__ == "__main__":
    run_full_ingestion()
