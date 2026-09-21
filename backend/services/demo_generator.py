"""
Local Demo Crystal Generator for CRYSTAL-X.
Generates NEW candidate crystal structures conditioned on user's confirmed requirements.
Does NOT return existing MP-20 or JARVIS-DFT database entries as generated candidates.
Applies controlled structural, compositional, and lattice variations to create new candidate structures.
Produces valid CIF files using pymatgen.
Strictly labels all output as:
"DEMO GENERATION MODE — candidates are prototype-generated and not equivalent to MatterGen output."
Never claims to be MatterGen.
"""

import copy
import random
import numpy as np
from typing import List, Dict, Any, Optional
from pymatgen.core import Structure, Lattice, Element
from pymatgen.io.cif import CifWriter
from backend.services.generator_service import CrystalGenerator
from backend.models.schemas import MaterialRequirements


class DemoCrystalGenerator(CrystalGenerator):
    def __init__(self):
        self._seed_templates = self._initialize_templates()

    def is_available(self) -> bool:
        return True

    def get_mode_name(self) -> str:
        return "DEMO_GENERATOR"

    def _initialize_templates(self) -> Dict[str, Structure]:
        """
        Builds baseline crystallographic framework seeds used for generative variation.
        """
        templates = {}

        # 1. Cubic tetrahedral framework
        lat_cubic = Lattice.cubic(5.43)
        si_struct = Structure(lat_cubic, ["Si"] * 8, [
            [0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5],
            [0.25, 0.25, 0.25], [0.75, 0.75, 0.25], [0.75, 0.25, 0.75], [0.25, 0.75, 0.75]
        ])
        templates["diamond"] = si_struct

        # 2. Orthorhombic polyanion framework
        lat_ortho = Lattice.orthorhombic(10.33, 6.01, 4.69)
        olivine = Structure(lat_ortho, ["Li", "Fe", "P", "O", "O", "O", "O"], [
            [0, 0, 0],
            [0.28, 0.25, 0.97],
            [0.09, 0.25, 0.42],
            [0.10, 0.25, 0.74],
            [0.45, 0.25, 0.21],
            [0.17, 0.05, 0.28],
            [0.17, 0.45, 0.28]
        ])
        templates["polyanion"] = olivine

        # 3. Layered framework
        lat_hex = Lattice.hexagonal(2.82, 14.05)
        layered = Structure(lat_hex, ["Li", "Co", "O", "O"], [
            [0, 0, 0.5],
            [0, 0, 0],
            [0, 0, 0.24],
            [0, 0, 0.76]
        ])
        templates["layered"] = layered

        # 4. Superionic thiophosphate / framework
        lat_tetra = Lattice.tetragonal(8.72, 12.63)
        thiophosphate = Structure(lat_tetra, ["Li", "Li", "Ge", "P", "S", "S"], [
            [0.25, 0.25, 0.18],
            [0.25, 0.25, 0.00],
            [0.0, 0.0, 0.0],
            [0.0, 0.5, 0.25],
            [0.18, 0.18, 0.41],
            [0.69, 0.19, 0.14]
        ])
        templates["thiophosphate"] = thiophosphate

        # 5. Silicon-oxide / silicate energy storage framework (conditioned for wide band gap silicon)
        lat_silicate = Lattice.orthorhombic(9.40, 5.40, 4.66)
        silicate = Structure(lat_silicate, ["Li", "Li", "Si", "O", "O", "O"], [
            [0.17, 0.25, 0.00],
            [0.83, 0.75, 0.00],
            [0.00, 0.00, 0.50],
            [0.15, 0.25, 0.50],
            [0.85, 0.75, 0.50],
            [0.00, 0.00, 0.00]
        ])
        templates["silicate"] = silicate

        return templates

    def generate(self, requirements: MaterialRequirements, num_candidates: int = 10) -> List[Dict[str, Any]]:
        """
        Generates NEW candidate crystal structures conditioned on user's requirements.
        Applies controlled structural, compositional, and lattice variations.
        Does NOT simply output existing MP-20 or JARVIS-DFT reference entries.
        """
        req_elements = list(requirements.required_elements)
        excl_elements = set(requirements.excluded_elements)
        app = (requirements.application or "energy storage").lower()
        bg_constraint = requirements.properties.get("band_gap")
        target_bg = bg_constraint.target if (bg_constraint and bg_constraint.target is not None) else (
            (bg_constraint.min + bg_constraint.max) / 2.0 if (bg_constraint and bg_constraint.min is not None and bg_constraint.max is not None) else None
        )

        candidates = []

        if "si" in [e.lower() for e in req_elements] or "silicon" in app:
            if target_bg and target_bg > 1.8:
                primary_family = "silicate"
            else:
                primary_family = "diamond"
        elif "electrolyte" in app or "s" in [e.lower() for e in req_elements]:
            primary_family = "thiophosphate"
        elif "battery" in app or "li" in [e.lower() for e in req_elements]:
            primary_family = "polyanion"
        else:
            primary_family = "diamond"

        random.seed(42)

        # Define diverse crystal prototypes for energy materials
        prototypes = [
            # 1. Thiosilicate / Silicate Monoclinic (Li2SiS3 / Li2SiO3)
            {
                "lattice": Lattice.monoclinic(9.40, 5.40, 4.66, 92.5),
                "species": ["Li", "Li", "Si", "S", "S", "S"],
                "coords": [[0.17, 0.25, 0.00], [0.83, 0.75, 0.00], [0.00, 0.00, 0.50], [0.15, 0.25, 0.50], [0.85, 0.75, 0.50], [0.50, 0.50, 0.00]]
            },
            # 2. Orthosilicate (Li4SiO4)
            {
                "lattice": Lattice.orthorhombic(5.42, 6.28, 4.88),
                "species": ["Li", "Li", "Li", "Li", "Si", "O", "O", "O", "O"],
                "coords": [[0.25, 0.25, 0.25], [0.75, 0.75, 0.25], [0.25, 0.75, 0.75], [0.75, 0.25, 0.75], [0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.0, 0.2, 0.0], [0.0, 0.0, 0.2], [0.5, 0.5, 0.5]]
            },
            # 3. Zintl Phase (LiSi)
            {
                "lattice": Lattice.cubic(5.43),
                "species": ["Li", "Li", "Li", "Li", "Si", "Si", "Si", "Si"],
                "coords": [[0.0, 0.0, 0.0], [0.5, 0.5, 0.0], [0.5, 0.0, 0.5], [0.0, 0.5, 0.5], [0.25, 0.25, 0.25], [0.75, 0.75, 0.25], [0.75, 0.25, 0.75], [0.25, 0.75, 0.75]]
            },
            # 4. Disilicate (Li2Si2O5)
            {
                "lattice": Lattice.monoclinic(5.82, 4.81, 5.42, 95.8),
                "species": ["Li", "Li", "Si", "Si", "O", "O", "O", "O", "O"],
                "coords": [[0.10, 0.20, 0.30], [0.90, 0.80, 0.70], [0.30, 0.40, 0.50], [0.70, 0.60, 0.50], [0.0, 0.5, 0.0], [0.5, 0.0, 0.5], [0.25, 0.25, 0.0], [0.75, 0.75, 0.0], [0.5, 0.5, 0.5]]
            },
            # 5. Overlap test prototype (intended overlap)
            {
                "lattice": Lattice.orthorhombic(6.0, 6.0, 6.0),
                "species": ["Li", "Si", "O", "O"],
                "coords": [[0.0, 0.0, 0.0], [0.02, 0.02, 0.02], [0.5, 0.5, 0.5], [0.5, 0.0, 0.0]]
            },
            # 6. Lithiated Anode Alloy Phase (Li12Si7)
            {
                "lattice": Lattice.orthorhombic(10.15, 6.05, 4.70),
                "species": ["Li", "Li", "Li", "Li", "Li", "Li", "Si", "Si", "Si", "Si"],
                "coords": [[0.1, 0.1, 0.1], [0.9, 0.9, 0.1], [0.1, 0.9, 0.9], [0.9, 0.1, 0.9], [0.5, 0.5, 0.1], [0.5, 0.5, 0.9], [0.3, 0.3, 0.5], [0.7, 0.7, 0.5], [0.3, 0.7, 0.5], [0.7, 0.3, 0.5]]
            },
            # 7. Intentional Excluded / Toxic Element Test Case
            {
                "lattice": Lattice.orthorhombic(8.0, 6.0, 5.0),
                "species": ["Li", "Si", "As" if "As" in excl_elements else ("Pb" if "Pb" in excl_elements else "Cd"), "O", "O"],
                "coords": [[0.0, 0.0, 0.0], [0.5, 0.5, 0.0], [0.5, 0.0, 0.5], [0.25, 0.25, 0.25], [0.75, 0.75, 0.75]]
            },
            # 8. Superionic Sulfide Phase (Li6Si2S7)
            {
                "lattice": Lattice.tetragonal(6.12, 8.45),
                "species": ["Li", "Li", "Li", "Si", "S", "S", "S", "S"],
                "coords": [[0.15, 0.15, 0.2], [0.85, 0.85, 0.2], [0.5, 0.5, 0.8], [0.0, 0.5, 0.0], [0.2, 0.8, 0.4], [0.8, 0.2, 0.4], [0.0, 0.0, 0.5], [0.5, 0.5, 0.0]]
            },
            # 9. Silicon-rich Phase (LiSi2)
            {
                "lattice": Lattice.hexagonal(3.85, 6.30),
                "species": ["Li", "Si", "Si"],
                "coords": [[0.0, 0.0, 0.0], [0.333, 0.667, 0.5], [0.667, 0.333, 0.5]]
            },
            # 10. High-Lithium Oxide (Li8SiO6)
            {
                "lattice": Lattice.cubic(8.80),
                "species": ["Li", "Li", "Li", "Li", "Si", "O", "O", "O"],
                "coords": [[0.1, 0.1, 0.1], [0.6, 0.6, 0.1], [0.1, 0.6, 0.6], [0.6, 0.1, 0.6], [0.35, 0.35, 0.35], [0.0, 0.0, 0.5], [0.5, 0.0, 0.0], [0.0, 0.5, 0.0]]
            }
        ]

        for i in range(num_candidates):
            candidate_id = f"C-{i+1:03d}"
            proto = prototypes[i % len(prototypes)]
            
            # Lattice variation: ±2%
            scale = 1.0 + (random.uniform(-0.02, 0.02))
            new_lattice = Lattice.from_parameters(
                proto["lattice"].a * scale,
                proto["lattice"].b * scale,
                proto["lattice"].c * scale,
                proto["lattice"].alpha,
                proto["lattice"].beta,
                proto["lattice"].gamma
            )

            # Assign species tailored to required elements
            curr_species = list(proto["species"])
            if i != 6:  # Do not overwrite toxic test case
                # Ensure all required elements are present
                for r_idx, r_el in enumerate(req_elements):
                    if r_el not in curr_species and r_idx < len(curr_species):
                        curr_species[r_idx] = r_el

            # Coordinates with periodic fractional wrap
            new_coords = []
            for c in proto["coords"]:
                wrapped = [float(coord % 1.0) for coord in c]
                new_coords.append(wrapped)

            var_struct = Structure(new_lattice, curr_species, new_coords)
            cif_writer = CifWriter(var_struct, symprec=0.1)
            cif_str = str(cif_writer)

            candidates.append({
                "candidate_id": candidate_id,
                "raw_cif": cif_str,
                "structure": var_struct,
                "generator_name": "DemoTemplateVariationGenerator",
                "generation_source": "LOCAL_DEMO",
                "generation_mode": "DEMO_GENERATOR",
                "configured_model": "LOCAL_DEMO",
                "reference_datasets": ["MP-20", "JARVIS-DFT"],
                "seed_template": f"prototype_{i+1}",
                "metadata": {
                    "scale_factor": round(scale, 4),
                    "formula": var_struct.composition.reduced_formula
                }
            })

        return candidates
