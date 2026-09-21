"""
CIF Service for CRYSTAL-X.
Handles CIF string generation, parsing user-uploaded CIFs, and batch packaging (zip files).
"""

import io
import os
import zipfile
from typing import List, Dict, Any, Optional, Tuple
from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter, CifParser
from pymatgen.io.vasp import Poscar


class CIFService:
    @staticmethod
    def structure_to_cif_string(struct: Structure) -> str:
        """
        Converts a pymatgen Structure to a formatted CIF string.
        """
        writer = CifWriter(struct, symprec=0.1)
        return str(writer)

    @staticmethod
    def parse_uploaded_cif(cif_content: str) -> Structure:
        """
        Parses an uploaded CIF string into a pymatgen Structure.
        Raises ValueError if unparseable.
        """
        parser = CifParser.from_str(cif_content)
        structures = parser.parse_structures(primitive=False)
        if not structures:
            raise ValueError("No valid crystal structure found in the provided CIF content.")
        return structures[0]

    @staticmethod
    def create_cif_zip_package(candidates: List[Dict[str, Any]]) -> bytes:
        """
        Creates an in-memory ZIP archive containing CIF files for multiple candidates.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cand in candidates:
                cand_id = cand.get("candidate_id", "cand")
                formula = cand.get("reduced_formula", "crystal").replace(" ", "")
                filename = f"{cand_id}_{formula}.cif"
                cif_str = cand.get("cif_string", "")
                zip_file.writestr(filename, cif_str)
        
        buf.seek(0)
        return buf.getvalue()
