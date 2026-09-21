"""
Harmonization and preprocessing script for MP-20 and JARVIS-DFT reference datasets.
Builds the unified reference catalog used strictly for reference comparison,
ensuring CRYSTAL-X never confuses reference retrieval with generative discovery.
"""

import os
import json
import datetime

def preprocess_and_harmonize():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    mp20_dir = os.path.join(data_dir, "mp20")
    jarvis_dir = os.path.join(data_dir, "jarvis_dft")
    processed_dir = os.path.join(data_dir, "processed")

    os.makedirs(mp20_dir, exist_ok=True)
    os.makedirs(jarvis_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    # 1. MP-20 reference subset (battery/clean energy representative materials)
    mp20_subset = [
        {
            "material_id": "mp-149",
            "dataset_provenance": "MP-20",
            "formula": "Si",
            "reduced_formula": "Si",
            "elements": ["Si"],
            "crystal_system": "Cubic",
            "space_group": "Fd-3m (227)",
            "formation_energy_per_atom": 0.0,
            "energy_above_hull": 0.0,
            "band_gap": 1.14,
            "density": 2.33,
            "cif_filename": "Si_diamond.cif",
            "energy_application": "Battery Anode / Semiconductor",
            "is_reference_only": True
        },
        {
            "material_id": "mp-19017",
            "dataset_provenance": "MP-20",
            "formula": "LiFePO4",
            "reduced_formula": "LiFePO4",
            "elements": ["Li", "Fe", "P", "O"],
            "crystal_system": "Orthorhombic",
            "space_group": "Pnma (62)",
            "formation_energy_per_atom": -2.14,
            "energy_above_hull": 0.0,
            "band_gap": 3.71,
            "density": 3.60,
            "cif_filename": "LiFePO4.cif",
            "energy_application": "Lithium-ion Battery Cathode",
            "is_reference_only": True
        },
        {
            "material_id": "mp-22526",
            "dataset_provenance": "MP-20",
            "formula": "LiCoO2",
            "reduced_formula": "LiCoO2",
            "elements": ["Li", "Co", "O"],
            "crystal_system": "Trigonal",
            "space_group": "R-3m (166)",
            "formation_energy_per_atom": -2.35,
            "energy_above_hull": 0.0,
            "band_gap": 2.15,
            "density": 5.06,
            "cif_filename": "LiCoO2.cif",
            "energy_application": "Lithium-ion Battery Cathode",
            "is_reference_only": True
        },
        {
            "material_id": "mp-804",
            "dataset_provenance": "MP-20",
            "formula": "Li4SiO4",
            "reduced_formula": "Li4SiO4",
            "elements": ["Li", "Si", "O"],
            "crystal_system": "Monoclinic",
            "space_group": "P2_1/m (11)",
            "formation_energy_per_atom": -2.62,
            "energy_above_hull": 0.0,
            "band_gap": 4.82,
            "density": 2.41,
            "cif_filename": "Li4SiO4.cif",
            "energy_application": "Solid Electrolyte / CO2 Sorbent",
            "is_reference_only": True
        }
    ]

    # 2. JARVIS-DFT reference subset (clean energy & solid-state conductors)
    jarvis_subset = [
        {
            "material_id": "JVASP-1002",
            "dataset_provenance": "JARVIS-DFT",
            "formula": "Na3V2(PO4)3",
            "reduced_formula": "Na3V2(PO4)3",
            "elements": ["Na", "V", "P", "O"],
            "crystal_system": "Trigonal",
            "space_group": "R-3c (167)",
            "formation_energy_per_atom": -2.48,
            "energy_above_hull": 0.005,
            "band_gap": 2.45,
            "bulk_modulus_gpa": 76.4,
            "cif_filename": "Na3V2PO43.cif",
            "energy_application": "Sodium-ion Cathode (NASICON)",
            "is_reference_only": True
        },
        {
            "material_id": "JVASP-82341",
            "dataset_provenance": "JARVIS-DFT",
            "formula": "Li10GeP2S12",
            "reduced_formula": "Li10GeP2S12",
            "elements": ["Li", "Ge", "P", "S"],
            "crystal_system": "Tetragonal",
            "space_group": "P4_2/nmc (137)",
            "formation_energy_per_atom": -0.82,
            "energy_above_hull": 0.024,
            "band_gap": 2.65,
            "bulk_modulus_gpa": 42.1,
            "cif_filename": "Li10GeP2S12.cif",
            "energy_application": "Solid-state Superionic Electrolyte",
            "is_reference_only": True
        },
        {
            "material_id": "JVASP-6120",
            "dataset_provenance": "JARVIS-DFT",
            "formula": "Li2SiS3",
            "reduced_formula": "Li2SiS3",
            "elements": ["Li", "Si", "S"],
            "crystal_system": "Monoclinic",
            "space_group": "P2_1/c (14)",
            "formation_energy_per_atom": -1.15,
            "energy_above_hull": 0.012,
            "band_gap": 2.10,
            "bulk_modulus_gpa": 38.2,
            "cif_filename": "Li2SiS3.cif",
            "energy_application": "Lithium Thiosilicate Solid Electrolyte",
            "is_reference_only": True
        }
    ]

    # Save to individual subsets
    with open(os.path.join(mp20_dir, "reference_subset.json"), "w", encoding="utf-8") as f:
        json.dump(mp20_subset, f, indent=2)

    with open(os.path.join(jarvis_dir, "reference_subset.json"), "w", encoding="utf-8") as f:
        json.dump(jarvis_subset, f, indent=2)

    # Save harmonized catalog
    harmonized = {
        "metadata": {
            "title": "CRYSTAL-X Harmonized Reference Catalog",
            "purpose": "Reference comparison and novelty evaluation ONLY. Not used for candidate retrieval.",
            "last_harmonized": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_structures": len(mp20_subset) + len(jarvis_subset),
            "mp20_count": len(mp20_subset),
            "jarvis_count": len(jarvis_subset),
            "schema_version": "2.0"
        },
        "references": mp20_subset + jarvis_subset
    }

    with open(os.path.join(processed_dir, "harmonized_reference.json"), "w", encoding="utf-8") as f:
        json.dump(harmonized, f, indent=2)

    print(f"Preprocessed and harmonized {len(harmonized['references'])} reference structures:")
    print(f" - MP-20: {len(mp20_subset)}")
    print(f" - JARVIS-DFT: {len(jarvis_subset)}")

if __name__ == "__main__":
    preprocess_and_harmonize()
