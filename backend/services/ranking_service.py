"""
Requirement-Driven Dynamic Ranking Engine for CRYSTAL-X.
Ranks candidates dynamically based on the current user's specific confirmed requirements.
Features:
- Weights derived dynamically from current requirements.
- Excludes unavailable properties from the denominator and renormalizes remaining weights.
  (Never assigns zero to a missing property).
- Multi-criteria score breakdown:
  * Stability Match
  * Band Gap Match
  * Chemistry & Structural Validity Match
  * Ionic Conductivity Match
  * Volume Change Match
  * Theoretical Capacity Match
- Categorizes requirement status: MATCH, PARTIAL, FAIL, REJECTED.
- Produces a transparent "Why this candidate ranked here" explanation checklist.
"""

from typing import Dict, Any, List, Optional
from backend.models.schemas import (
    RankingWeights,
    RankingScoreBreakdown,
    PropertyPredictions,
    MaterialRequirements,
    StructuralValidationResult,
    RequirementMatchInfo,
    PhenomenaValidationResult,
    Candidate
)


class MultiCriteriaRankingEngine:
    @staticmethod
    def calculate_score(
        predictions: PropertyPredictions,
        validation: StructuralValidationResult,
        requirements: MaterialRequirements,
        phenomena: Optional[PhenomenaValidationResult] = None,
        weights: Optional[RankingWeights] = None,
        compliance_status: str = "MATCH"
    ) -> RankingScoreBreakdown:
        """
        Calculates normalized requirement-match score (0-100) dynamically depending on user's requirements.
        """
        w = weights or requirements.ranking_weights
        notes: List[str] = []
        effective_w: Dict[str, float] = {}

        # 1. Stability Score (0 - 100)
        # Minimizes energy above hull relative to target or screening threshold
        ehull = predictions.energy_above_hull.value
        stability_score: Optional[float] = None
        if ehull is not None:
            ehull_req = requirements.properties.get("energy_above_hull")
            target_ehull = ehull_req.max if (ehull_req and ehull_req.max is not None) else 0.08
            # Higher score for lower energy above hull
            stability_score = max(0.0, min(100.0, 100.0 * (1.0 - (ehull / (target_ehull * 1.8)))))
            stability_score = round(stability_score, 1)

        # 2. Band Gap Requirement Match Score (0 - 100)
        bg = predictions.band_gap.value
        band_gap_score: Optional[float] = None
        bg_req = requirements.properties.get("band_gap")
        if bg is not None:
            if bg_req and bg_req.min is not None and bg_req.max is not None:
                # Target range specified, e.g. 1.5 to 2.2 eV
                if bg_req.min <= bg <= bg_req.max:
                    band_gap_score = 100.0
                else:
                    dist = min(abs(bg - bg_req.min), abs(bg - bg_req.max))
                    band_gap_score = max(0.0, min(100.0, 100.0 * (1.0 - (dist / 1.0))))
            elif bg_req and bg_req.min is not None:
                if bg >= bg_req.min:
                    band_gap_score = 100.0
                else:
                    dist = bg_req.min - bg
                    band_gap_score = max(0.0, min(100.0, 100.0 * (1.0 - (dist / 1.0))))
            elif bg_req and bg_req.target is not None:
                diff = abs(bg - bg_req.target)
                tol = bg_req.tolerance or 0.3
                band_gap_score = max(0.0, min(100.0, 100.0 * (1.0 - (diff / (tol * 2.0)))))
            else:
                band_gap_score = 85.0 if bg > 0.5 else 50.0
            band_gap_score = round(band_gap_score, 1)

        # 3. Chemistry & Structural Validity Score (0 - 100)
        chemistry_score: float = 100.0
        if not validation.is_valid:
            chemistry_score -= 50.0
        if compliance_status in ("FAIL", "REJECTED"):
            chemistry_score -= 40.0
        if validation.overlap_heuristic_flag:
            chemistry_score -= 30.0
        chemistry_score = max(0.0, min(100.0, round(chemistry_score, 1)))

        # 4. Conductivity Score (0 - 100 or None if NOT_AVAILABLE)
        conductivity_score: Optional[float] = None
        cond_val = predictions.ionic_conductivity.value
        if cond_val is not None:
            import math
            log_c = math.log10(max(1e-9, cond_val))
            conductivity_score = max(0.0, min(100.0, (log_c + 6.0) / 4.0 * 100.0))
            conductivity_score = round(conductivity_score, 1)

        # 5. Volume Change Score (0 - 100)
        volume_change_score: Optional[float] = None
        vol_req = requirements.properties.get("volume_change")
        if predictions.volume_change and predictions.volume_change.value is not None:
            dv = predictions.volume_change.value
            max_limit = vol_req.max if (vol_req and vol_req.max is not None) else 6.0
            volume_change_score = max(0.0, min(100.0, 100.0 * (1.0 - (dv / (max_limit * 1.5)))))
            volume_change_score = round(volume_change_score, 1)

        # 6. Capacity Score (0 - 100)
        capacity_score: Optional[float] = None
        if predictions.capacity and predictions.capacity.value is not None:
            cap_val = predictions.capacity.value
            cap_req = requirements.properties.get("capacity")
            target_cap = cap_req.target if (cap_req and cap_req.target is not None) else 200.0
            capacity_score = max(0.0, min(100.0, (cap_val / target_cap) * 80.0))
            capacity_score = round(capacity_score, 1)

        # Weight Renormalization Across Available Properties
        available_components = {}
        if stability_score is not None:
            available_components["stability"] = (stability_score, w.stability)
        if band_gap_score is not None:
            available_components["band_gap"] = (band_gap_score, w.band_gap)
        if chemistry_score is not None:
            available_components["chemistry"] = (chemistry_score, w.chemistry)
        if conductivity_score is not None:
            available_components["ionic_conductivity"] = (conductivity_score, w.ionic_conductivity)
        else:
            notes.append("Ionic conductivity unavailable: weight renormalized across available properties.")

        if volume_change_score is not None and "volume_change" in requirements.properties:
            available_components["volume_change"] = (volume_change_score, 0.15)
        if capacity_score is not None and "capacity" in requirements.properties:
            available_components["capacity"] = (capacity_score, 0.15)

        sum_raw_weights = sum(weight for _, weight in available_components.values())

        if sum_raw_weights > 0:
            for k, (score, raw_w) in available_components.items():
                effective_w[k] = round(raw_w / sum_raw_weights, 4)
        else:
            for k in available_components.keys():
                effective_w[k] = round(1.0 / len(available_components), 4)

        total_score = 0.0
        for k, (score, _) in available_components.items():
            total_score += score * effective_w[k]

        total_score = round(min(100.0, max(0.0, total_score)), 1)

        expl_parts = []
        for k, eff_wt in effective_w.items():
            score_val = available_components[k][0]
            expl_parts.append(f"{k.replace('_', ' ').title()} ({score_val:.0f} × {eff_wt*100:.1f}%)")

        explanation = f"Match Score: {total_score}/100 based on " + ", ".join(expl_parts)

        return RankingScoreBreakdown(
            stability_score=stability_score,
            band_gap_score=band_gap_score,
            conductivity_score=conductivity_score,
            chemistry_score=chemistry_score,
            volume_change_score=volume_change_score,
            capacity_score=capacity_score,
            effective_weights=effective_w,
            total_score=total_score,
            explanation=explanation,
            ranking_notes=notes
        )

    @classmethod
    def generate_ranking_explanation(
        cls,
        candidate: Candidate,
        requirements: MaterialRequirements
    ) -> List[str]:
        """
        Generates structured 'Why this candidate ranked here' checklist.
        """
        checklist = []

        # 1. Structural Validity Check
        if candidate.validation.is_valid:
            checklist.append("✓ Crystallographically valid unit cell & finite lattice parameters")
        else:
            checklist.append(f"✗ Crystallographic invalidity: {', '.join(candidate.validation.reasons)}")

        # 2. Hard Exclusion Check
        if requirements.excluded_elements:
            violating = set(requirements.excluded_elements).intersection(set(candidate.elements))
            if not violating:
                checklist.append(f"✓ Zero prohibited elements present ({', '.join(requirements.excluded_elements)} completely excluded)")
            else:
                checklist.append(f"✗ Prohibited element violation: contains {', '.join(violating)}")

        # 3. Required Elements Check
        if requirements.required_elements:
            missing = set(requirements.required_elements) - set(candidate.elements)
            if not missing:
                checklist.append(f"✓ All required elements present ({', '.join(requirements.required_elements)})")
            else:
                checklist.append(f"✗ Missing required elements: {', '.join(missing)}")

        # 4. Band Gap Match Check
        bg = candidate.predictions.band_gap.value
        bg_req = requirements.properties.get("band_gap")
        if bg is not None and bg_req:
            if bg_req.min is not None and bg_req.max is not None:
                if bg_req.min <= bg <= bg_req.max:
                    checklist.append(f"✓ Band gap {bg:.2f} eV directly matches requested range ({bg_req.min}–{bg_req.max} eV)")
                else:
                    checklist.append(f"⚠ Band gap {bg:.2f} eV outside requested range ({bg_req.min}–{bg_req.max} eV)")
            elif bg_req.min is not None:
                if bg >= bg_req.min:
                    checklist.append(f"✓ Band gap {bg:.2f} eV satisfies minimum > {bg_req.min} eV")
                else:
                    checklist.append(f"⚠ Band gap {bg:.2f} eV below minimum > {bg_req.min} eV")
        elif bg is not None:
            checklist.append(f"ℹ Band gap predicted: {bg:.2f} eV")

        # 5. Stability Check
        ehull = candidate.predictions.energy_above_hull.value
        ehull_req = requirements.properties.get("energy_above_hull")
        if ehull is not None:
            if ehull_req and ehull_req.max is not None:
                if ehull <= ehull_req.max:
                    checklist.append(f"✓ Energy above hull {ehull:.3f} eV/atom meets hard limit (< {ehull_req.max} eV/atom)")
                else:
                    checklist.append(f"⚠ Energy above hull {ehull:.3f} eV/atom exceeds limit (< {ehull_req.max} eV/atom)")
            else:
                checklist.append(f"✓ Energy above hull {ehull:.3f} eV/atom satisfies low-energy thermodynamic preference")

        # 6. Volume Change Check
        if candidate.volume_change and candidate.volume_change.volume_change_percent is not None:
            dv = candidate.volume_change.volume_change_percent
            if candidate.volume_change.passed:
                checklist.append(f"✓ Low volume change ({dv:.1f}%) during mobile ion transport")
            else:
                checklist.append(f"⚠ Volume change ({dv:.1f}%) exceeds constraint limit")

        # 7. Novelty / Reference Verdict
        if candidate.novelty:
            checklist.append(f"ℹ Reference Verdict: {candidate.novelty.result}")

        return checklist

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[Candidate],
        requirements: MaterialRequirements,
        weights: Optional[RankingWeights] = None
    ) -> List[Candidate]:
        """
        Calculates match scores and sorts surviving candidates.
        Assigns rank and rank_label (#1 Best Requirement Match, etc.).
        """
        for c in candidates:
            # Recompute dynamic score
            c.ranking = cls.calculate_score(
                c.predictions,
                c.validation,
                requirements,
                c.phenomena,
                weights=weights,
                compliance_status=c.requirement_status
            )
            # Recompute explanation checklist
            c.ranking_explanation = cls.generate_ranking_explanation(c, requirements)
            
            c.requirement_match = RequirementMatchInfo(
                compliance_status=c.requirement_status,
                score=c.ranking.total_score,
                rank_label=None,
                ranking_title="Ranked according to your confirmed material requirements"
            )

        # Sort descending by total score
        sorted_candidates = sorted(candidates, key=lambda x: x.ranking.total_score, reverse=True)

        # Assign ranks and labels
        for idx, cand in enumerate(sorted_candidates):
            rank_num = idx + 1
            cand.rank = rank_num
            if rank_num == 1:
                label = "#1 Best Requirement Match"
            elif rank_num == 2:
                label = "#2 Second Requirement Match"
            elif rank_num == 3:
                label = "#3 Third Requirement Match"
            else:
                label = f"#{rank_num} Requirement Match"
            cand.rank_label = label
            cand.requirement_match.rank_label = label

        return sorted_candidates
