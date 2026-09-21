"""
DFT Validation Queue Service for CRYSTAL-X.
Manages candidates queued for downstream ab initio Density Functional Theory (DFT) calculations.
Exports complete DFT preparation packages to exports/dft_queue/.
Clearly declares: "DFT validation is downstream and is not performed by this prototype."
"""

import os
import json
import zipfile
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser
from pymatgen.io.vasp import Poscar
from backend.models.schemas import DFTQueueItem, DFTExportResponse


class DFTQueueService:
    def __init__(self, export_root: Optional[str] = None):
        if not export_root:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            export_root = os.path.join(base_dir, "exports", "dft_queue")
        self.export_root = export_root
        os.makedirs(self.export_root, exist_ok=True)
        self._queue: Dict[str, DFTQueueItem] = {}

    def add_to_queue(self, item: DFTQueueItem) -> bool:
        self._queue[item.candidate_id] = item
        return True

    def remove_from_queue(self, candidate_id: str) -> bool:
        if candidate_id in self._queue:
            del self._queue[candidate_id]
            return True
        return False

    def get_queue(self) -> List[DFTQueueItem]:
        return list(self._queue.values())

    def is_in_queue(self, candidate_id: str) -> bool:
        return candidate_id in self._queue

    def export_package(self) -> DFTExportResponse:
        """
        Exports all queued candidates to filesystem folder and prepares a downloadable ZIP.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(self.export_root, f"batch_{timestamp}")
        os.makedirs(batch_dir, exist_ok=True)

        exported_ids = []

        incar_template = """# Standard VASP Relaxation INCAR for Energy Materials
SYSTEM = CRYSTAL-X Downstream Candidate
PREC = Accurate
ENCUT = 520
IBRION = 2
ISIF = 3
NSW = 99
EDIFF = 1E-6
EDIFFG = -0.01
ISMEAR = 0
SIGMA = 0.05
LREAL = Auto
LWAVE = .FALSE.
LCHARG = .FALSE.
"""

        disclaimer_text = """========================================================================
CRYSTAL-X DOWNSTREAM DFT VALIDATION PACKAGE
========================================================================
DISCLAIMER:
DFT validation is downstream and is not performed by this prototype.
AI-generated candidates are computational proposals. Structural validity
and ML predictions do not constitute proof of thermodynamic stability,
synthesizability, or experimental performance. High-priority candidates
require higher-fidelity computational and experimental validation.
========================================================================
"""

        with open(os.path.join(batch_dir, "DISCLAIMER.txt"), "w", encoding="utf-8") as f:
            f.write(disclaimer_text)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("DISCLAIMER.txt", disclaimer_text)

            for cand_id, item in self._queue.items():
                cand_subdir = os.path.join(batch_dir, cand_id)
                os.makedirs(cand_subdir, exist_ok=True)

                # 1. CIF
                cif_fn = f"{cand_id}_{item.formula.replace(' ', '')}.cif"
                cif_path = os.path.join(cand_subdir, cif_fn)
                with open(cif_path, "w", encoding="utf-8") as f:
                    f.write(item.cif_string)
                zf.writestr(f"{cand_id}/{cif_fn}", item.cif_string)

                # 2. POSCAR (if pymatgen can parse)
                try:
                    parser = CifParser.from_str(item.cif_string)
                    struct = parser.parse_structures(primitive=False)[0]
                    poscar = Poscar(struct)
                    poscar_str = str(poscar)
                    with open(os.path.join(cand_subdir, "POSCAR"), "w", encoding="utf-8") as f:
                        f.write(poscar_str)
                    zf.writestr(f"{cand_id}/POSCAR", poscar_str)
                except Exception:
                    pass

                # 3. INCAR template
                with open(os.path.join(cand_subdir, "INCAR"), "w", encoding="utf-8") as f:
                    f.write(incar_template)
                zf.writestr(f"{cand_id}/INCAR", incar_template)

                # 4. Metadata JSON
                meta = {
                    "candidate_id": cand_id,
                    "formula": item.formula,
                    "predicted_properties": item.predicted_properties,
                    "ranking_score": item.ranking_score,
                    "reason_selected": item.reason_selected,
                    "queued_at": item.added_at,
                    "status": item.status,
                    "disclaimer": "DFT validation is downstream and is not performed by this prototype."
                }
                meta_json = json.dumps(meta, indent=2)
                with open(os.path.join(cand_subdir, "metadata.json"), "w", encoding="utf-8") as f:
                    f.write(meta_json)
                zf.writestr(f"{cand_id}/metadata.json", meta_json)

                exported_ids.append(cand_id)

        # Write the zip file
        zip_path = os.path.join(batch_dir, f"dft_package_{timestamp}.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_buf.getvalue())

        return DFTExportResponse(
            export_dir=batch_dir,
            exported_candidates=exported_ids,
            package_zip_path=zip_path,
            disclaimer="DFT validation is downstream and is not performed by this prototype."
        )
