"""
Data Service for CRYSTAL-X.
Manages candidate persistence, job state, reference materials library from the
139,131-structure reference database (MP-20 and JARVIS-DFT), and real-time statistics.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.models.schemas import Candidate, MaterialRequirements


class DataService:
    def __init__(self, data_root: Optional[str] = None):
        if not data_root:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_root = os.path.join(base_dir, "data")
        self.data_root = data_root
        self.db_path = os.path.join(data_root, "reference_catalog.db")
        self._candidates: Dict[str, Candidate] = {}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._reference_materials = self._load_initial_reference_materials()

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                conn.row_factory = sqlite3.Row
                return conn
            except Exception:
                return None
        return None

    def _load_initial_reference_materials(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Loads a representative set of reference materials from catalog DB or fallback."""
        conn = self._get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT material_id, dataset_source, dataset_split, formula, reduced_formula,
                           chemical_system, elements_json, crystal_system, space_group, space_group_number,
                           formation_energy_per_atom, energy_above_hull, band_gap, density, nsites, properties_json
                    FROM reference_materials
                    WHERE energy_above_hull IS NOT NULL
                    ORDER BY energy_above_hull ASC, formula ASC
                    LIMIT ?
                """, (limit,))
                rows = cur.fetchall()
                materials = []
                for r in rows:
                    ehull = r["energy_above_hull"]
                    is_stable = (ehull is not None and ehull <= 0.05)
                    try:
                        elems = json.loads(r["elements_json"]) if r["elements_json"] else []
                    except Exception:
                        elems = []

                    materials.append({
                        "material_id": r["material_id"],
                        "pretty_formula": r["formula"],
                        "formula": r["formula"],
                        "reduced_formula": r["reduced_formula"],
                        "dataset_source": r["dataset_source"],
                        "dataset_split": r["dataset_split"],
                        "source": f"{r['dataset_source']} ({r['dataset_split']})" if r["dataset_split"] else r["dataset_source"],
                        "chemical_system": r["chemical_system"],
                        "elements": elems,
                        "crystal_system": r["crystal_system"] or "Unknown",
                        "space_group": r["space_group"] or (f"#{r['space_group_number']}" if r["space_group_number"] else "Unknown"),
                        "space_group_number": r["space_group_number"],
                        "formation_energy_per_atom": r["formation_energy_per_atom"],
                        "energy_above_hull": r["energy_above_hull"],
                        "band_gap": r["band_gap"],
                        "density": r["density"],
                        "nsites": r["nsites"],
                        "is_stable": is_stable,
                        "application_tags": [r["dataset_source"], "Reference Benchmark"]
                    })
                conn.close()
                if materials:
                    return materials
            except Exception:
                if conn:
                    conn.close()

        # Fallback to sample materials if DB not available
        path = os.path.join(self.data_root, "sample_materials", "known_materials.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_reference_materials(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self._reference_materials:
            self._reference_materials = self._load_initial_reference_materials(limit)
        return self._reference_materials[:limit]

    def search_reference_materials(
        self,
        query: Optional[str] = None,
        dataset_source: Optional[str] = None,
        element: Optional[str] = None,
        max_ehull: Optional[float] = None,
        min_band_gap: Optional[float] = None,
        stable_only: bool = False,
        limit: int = 24,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Fast SQL search and pagination across 139,131 reference crystal structures.
        """
        conn = self._get_connection()
        if not conn:
            return {
                "total_records": len(self._reference_materials),
                "page": page,
                "limit": limit,
                "materials": self._reference_materials[:limit]
            }

        try:
            cur = conn.cursor()
            conditions = []
            params = []

            if dataset_source and dataset_source.upper() in ["MP-20", "JARVIS-DFT"]:
                conditions.append("dataset_source = ?")
                params.append(dataset_source.upper())

            if query and query.strip():
                q = query.strip()
                # Check if it matches an exact ID, formula, or chemical system
                conditions.append("(material_id LIKE ? OR formula LIKE ? OR chemical_system LIKE ?)")
                params.extend([f"{q}%", f"{q}%", f"%{q}%"])

            if element and element.strip():
                el = element.strip().capitalize()
                # Match in chemical system, e.g. "K", "Fe-K", "K-O"
                conditions.append("(chemical_system = ? OR chemical_system LIKE ? OR chemical_system LIKE ? OR chemical_system LIKE ?)")
                params.extend([el, f"{el}-%", f"%-{el}-%", f"%-{el}"])

            if stable_only:
                conditions.append("energy_above_hull IS NOT NULL AND energy_above_hull <= 0.05")
            elif max_ehull is not None:
                conditions.append("energy_above_hull IS NOT NULL AND energy_above_hull <= ?")
                params.append(max_ehull)

            if min_band_gap is not None:
                conditions.append("band_gap IS NOT NULL AND band_gap >= ?")
                params.append(min_band_gap)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Count total matching
            count_sql = f"SELECT COUNT(*) FROM reference_materials {where_clause}"
            cur.execute(count_sql, params)
            total_matching = cur.fetchone()[0]

            # Fetch page
            offset = max(0, (page - 1) * limit)
            select_sql = f"""
                SELECT material_id, dataset_source, dataset_split, formula, reduced_formula,
                       chemical_system, elements_json, crystal_system, space_group, space_group_number,
                       formation_energy_per_atom, energy_above_hull, band_gap, density, nsites
                FROM reference_materials
                {where_clause}
                ORDER BY
                    CASE WHEN energy_above_hull IS NULL THEN 1 ELSE 0 END,
                    energy_above_hull ASC,
                    formula ASC
                LIMIT ? OFFSET ?
            """
            cur.execute(select_sql, params + [limit, offset])
            rows = cur.fetchall()

            materials = []
            for r in rows:
                ehull = r["energy_above_hull"]
                is_stable = (ehull is not None and ehull <= 0.05)
                try:
                    elems = json.loads(r["elements_json"]) if r["elements_json"] else []
                except Exception:
                    elems = []

                materials.append({
                    "material_id": r["material_id"],
                    "pretty_formula": r["formula"],
                    "formula": r["formula"],
                    "reduced_formula": r["reduced_formula"],
                    "dataset_source": r["dataset_source"],
                    "dataset_split": r["dataset_split"],
                    "source": f"{r['dataset_source']} ({r['dataset_split']})" if r["dataset_split"] else r["dataset_source"],
                    "chemical_system": r["chemical_system"],
                    "elements": elems,
                    "crystal_system": r["crystal_system"] or "Unknown",
                    "space_group": r["space_group"] or (f"#{r['space_group_number']}" if r["space_group_number"] else "Unknown"),
                    "space_group_number": r["space_group_number"],
                    "formation_energy_per_atom": r["formation_energy_per_atom"],
                    "energy_above_hull": r["energy_above_hull"],
                    "band_gap": r["band_gap"],
                    "density": r["density"],
                    "nsites": r["nsites"],
                    "is_stable": is_stable,
                    "application_tags": [r["dataset_source"], "Reference Benchmark"]
                })

            return {
                "total_records": total_matching,
                "page": page,
                "limit": limit,
                "total_pages": (total_matching + limit - 1) // limit if limit > 0 else 1,
                "materials": materials
            }
        finally:
            conn.close()

    def store_candidate(self, candidate: Candidate):
        self._candidates[candidate.candidate_id] = candidate

    def store_candidates(self, candidates: List[Candidate]):
        for c in candidates:
            self._candidates[c.candidate_id] = c

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        return self._candidates.get(candidate_id)

    def get_all_candidates(self) -> List[Candidate]:
        cand_list = list(self._candidates.values())
        cand_list.sort(key=lambda x: (x.rank is None, x.rank or 9999))
        return cand_list

    def clear_candidates(self):
        self._candidates.clear()

    def store_job(self, job_id: str, job_data: Dict[str, Any]):
        self._jobs[job_id] = job_data

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def get_dashboard_stats(self, dft_queue_count: int = 0) -> Dict[str, int]:
        cands = list(self._candidates.values())
        total_generated = len(cands)
        valid = sum(1 for c in cands if c.validation.is_valid)
        invalid = total_generated - valid
        passed_screening = sum(1 for c in cands if c.screening.passed)
        potentially_novel = sum(1 for c in cands if "Potentially novel" in c.novelty.verdict_label or "No close match" in c.novelty.verdict_label)
        top_ranked = sum(1 for c in cands if c.ranking.total_score >= 75.0)

        return {
            "generated": total_generated,
            "valid": valid,
            "invalid": invalid,
            "passed_screening": passed_screening,
            "potentially_novel": potentially_novel,
            "top_ranked": top_ranked,
            "dft_queue": dft_queue_count
        }
