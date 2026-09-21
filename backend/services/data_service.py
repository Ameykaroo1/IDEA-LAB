"""
Data Service for CRYSTAL-X.
Manages candidate persistence, job state, reference materials library,
and real-time prototype statistics.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.models.schemas import Candidate, MaterialRequirements


class DataService:
    def __init__(self, data_root: Optional[str] = None):
        if not data_root:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_root = os.path.join(base_dir, "data")
        self.data_root = data_root
        self._candidates: Dict[str, Candidate] = {}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._reference_materials = self._load_reference_materials()

    def _load_reference_materials(self) -> List[Dict[str, Any]]:
        path = os.path.join(self.data_root, "sample_materials", "known_materials.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_reference_materials(self) -> List[Dict[str, Any]]:
        return self._reference_materials

    def store_candidate(self, candidate: Candidate):
        self._candidates[candidate.candidate_id] = candidate

    def store_candidates(self, candidates: List[Candidate]):
        for c in candidates:
            self._candidates[c.candidate_id] = c

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        return self._candidates.get(candidate_id)

    def get_all_candidates(self) -> List[Candidate]:
        # Return sorted by rank if ranked
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
        potentially_novel = sum(1 for c in cands if "Potentially novel" in c.novelty.verdict_label)
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
