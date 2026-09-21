"""
Natural Language Requirement Extraction Service for CRYSTAL-X.
Uses a hybrid approach (regular expressions, chemical element catalog,
property patterns, and unit normalization) to extract structured crystal material constraints.
Does NOT decide whether a crystal is scientifically valid or stable.
"""

import re
import json
import os
from typing import Dict, Any, List, Tuple, Optional
from backend.models.schemas import MaterialRequirements, PropertyConstraint, StructuralConstraints, RankingWeights


class NLPRequirementService:
    def __init__(self, elements_path: Optional[str] = None):
        if not elements_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            elements_path = os.path.join(base_dir, "data", "metadata", "elements.json")
        
        self.elements_dict = {}
        self.element_name_to_symbol = {}
        self.toxic_elements = set()
        
        if os.path.exists(elements_path):
            with open(elements_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.elements_dict = data.get("elements", {})
                for sym, info in self.elements_dict.items():
                    name = info.get("name", "").lower()
                    self.element_name_to_symbol[name] = sym
                    self.element_name_to_symbol[sym.lower()] = sym
                    if info.get("toxic", False):
                        self.toxic_elements.add(sym)

        # Common aliases & compounds
        self.common_aliases = {
            "silicon": "Si",
            "lithium": "Li",
            "sodium": "Na",
            "potassium": "K",
            "magnesium": "Mg",
            "iron": "Fe",
            "cobalt": "Co",
            "nickel": "Ni",
            "manganese": "Mn",
            "titanium": "Ti",
            "vanadium": "V",
            "oxygen": "O",
            "sulfur": "S",
            "phosphorus": "P",
            "germanium": "Ge",
            "zirconium": "Zr",
            "lead": "Pb",
            "cadmium": "Cd",
            "mercury": "Hg",
            "arsenic": "As",
            "antimony": "Sb",
            "thallium": "Tl",
            "aluminum": "Al",
            "copper": "Cu",
            "zinc": "Zn",
            "carbon": "C"
        }
        for k, v in self.common_aliases.items():
            self.element_name_to_symbol[k] = v

    def parse_text(self, text: str) -> Dict[str, Any]:
        """
        Parses raw natural language text into extracted structured entities.
        Returns a dictionary containing raw extracted fields, confidences, ambiguities,
        and warnings.
        """
        if not text or not text.strip():
            return {
                "raw_text": "",
                "application": "Custom / Unspecified",
                "required_elements": [],
                "allowed_elements": [],
                "excluded_elements": [],
                "properties": {},
                "structural_constraints": {},
                "confidences": {},
                "ambiguities": ["Input text is empty. Please provide a description of your target material."],
                "warnings": ["No constraints extracted."],
                "needs_confirmation": True,
                "extraction_steps": [
                    "Input text was empty or whitespace only."
                ]
            }

        steps = [
            "Understanding application...",
            "Detecting elements & chemical composition...",
            "Identifying excluded and toxic elements...",
            "Extracting target properties (band gap, stability, conductivity)...",
            "Extracting numerical ranges & normalizing units...",
            "Building structured material requirements..."
        ]

        confidences: Dict[str, str] = {}
        ambiguities: List[str] = []
        warnings: List[str] = []

        # 1. Application & Domain extraction
        application = self._extract_application(text)
        energy_domain = self._classify_domain(text)
        battery_type = self._extract_battery_type(text)
        confidences["application"] = "High" if application != "Energy storage" else "Medium"
        confidences["energy_domain"] = "High"

        # 2. Excluded elements extraction
        excluded_elements = self._extract_excluded_elements(text)
        if excluded_elements:
            confidences["excluded_elements"] = "High"

        # 3. Required & preferred elements extraction
        required_elements = self._extract_required_elements(text, excluded_elements)
        if required_elements:
            confidences["required_elements"] = "High"
        else:
            ambiguities.append("No specific required elements explicitly identified in the text.")

        preferred_elements = self._extract_preferred_elements(text, required_elements, excluded_elements)
        if preferred_elements:
            confidences["preferred_elements"] = "High"

        # 4. Properties extraction
        properties: Dict[str, PropertyConstraint] = {}

        # Band gap
        bg_constraint = self._extract_band_gap(text)
        if bg_constraint:
            properties["band_gap"] = bg_constraint
            confidences["band_gap"] = bg_constraint.confidence or "High"

        # Energy above hull / stability
        hull_constraint = self._extract_energy_above_hull(text)
        if hull_constraint:
            properties["energy_above_hull"] = hull_constraint
            confidences["energy_above_hull"] = hull_constraint.confidence or "High"
            if hull_constraint.preference and hull_constraint.max is None:
                ambiguities.append("Stability preference specified as qualitative ('low'/'stable') without exact eV/atom threshold.")

        # Ionic conductivity
        cond_constraint = self._extract_ionic_conductivity(text)
        if cond_constraint:
            properties["ionic_conductivity"] = cond_constraint
            confidences["ionic_conductivity"] = cond_constraint.confidence or "High"
            if cond_constraint.preference and cond_constraint.target is None:
                ambiguities.append("Ionic conductivity preference specified as qualitative ('high') without numerical S/cm threshold.")

        # Capacity
        cap_constraint = self._extract_capacity(text)
        if cap_constraint:
            properties["capacity"] = cap_constraint
            confidences["capacity"] = cap_constraint.confidence or "High"

        # Volume change
        vol_change_constraint = self._extract_volume_change(text)
        if vol_change_constraint:
            properties["volume_change"] = vol_change_constraint
            confidences["volume_change"] = vol_change_constraint.confidence or "High"

        # 5. Material type extraction
        material_type = self._extract_material_type(text)

        # 6. Check missing info
        if not properties and not required_elements:
            warnings.append("Additional material constraints (chemistry, band gap, stability) were not specified.")

        return {
            "raw_text": text,
            "application": application,
            "energy_domain": energy_domain,
            "battery_type": battery_type,
            "material_type": material_type,
            "required_elements": required_elements,
            "preferred_elements": preferred_elements,
            "allowed_elements": [],
            "excluded_elements": excluded_elements,
            "properties": properties,
            "structural_constraints": StructuralConstraints(),
            "confidences": confidences,
            "ambiguities": ambiguities,
            "warnings": warnings,
            "needs_confirmation": True,
            "extraction_steps": steps
        }

    def _classify_domain(self, text: str) -> str:
        text_lower = text.lower()
        if "solid electrolyte" in text_lower or "solid-state electrolyte" in text_lower:
            return "SOLID_ELECTROLYTE"
        if "cathode" in text_lower or "positive electrode" in text_lower:
            return "CATHODE"
        if "anode" in text_lower or "negative electrode" in text_lower:
            return "ANODE"
        if "ionic conductivity" in text_lower or "ion conductor" in text_lower or "superionic" in text_lower:
            return "IONIC_CONDUCTOR"
        if "battery" in text_lower or "li-ion" in text_lower or "lithium-ion" in text_lower or "sodium-ion" in text_lower:
            return "BATTERY"
        if "energy-storage" in text_lower or "energy storage" in text_lower:
            return "ENERGY_STORAGE"
        return "BATTERY"

    def _extract_battery_type(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        has_solid = "solid" in text_lower or "solid-state" in text_lower or "electrolyte" in text_lower
        if "na" in text_lower or "sodium" in text_lower:
            return "sodium_ion_solid_state" if has_solid else "sodium_ion"
        if "k" in text_lower or "potassium" in text_lower:
            return "potassium_ion"
        if "mg" in text_lower or "magnesium" in text_lower:
            return "magnesium_ion"
        if "zn" in text_lower or "zinc" in text_lower:
            return "zinc_ion"
        if "li" in text_lower or "lithium" in text_lower:
            return "lithium_ion_solid_state" if has_solid else "lithium_ion"
        if has_solid:
            return "solid_state_battery"
        return "lithium_ion"

    def _extract_preferred_elements(self, text: str, required: List[str], excluded: List[str]) -> List[str]:
        preferred = set()
        pref_patterns = [
            r"(?:prefer|preferably|optional|optionally|favouring|favoring|doped with|doping with)\s+([^.;,]+)",
            r"with or without\s+([^.;,]+)"
        ]
        for pat in pref_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                span = m.group(1)
                found = self._find_elements_in_span(span)
                for f in found:
                    if f not in required and f not in excluded:
                        preferred.add(f)
        return sorted(list(preferred))

    def _extract_application(self, text: str) -> str:
        text_lower = text.lower()
        if "solid electrolyte" in text_lower or "electrolyte" in text_lower or "ion conductor" in text_lower:
            return "Solid electrolyte"
        if "battery electrode" in text_lower or "cathode" in text_lower or "anode" in text_lower or "battery material" in text_lower:
            return "Battery electrode"
        if "solar" in text_lower or "photovoltaic" in text_lower:
            return "Solar/energy material"
        if "energy storage" in text_lower or "supercapacitor" in text_lower:
            return "Energy storage"
        return "Energy storage"

    def _extract_excluded_elements(self, text: str) -> List[str]:
        excluded = set()
        text_lower = text.lower()

        # Toxic element catch-all
        if "without toxic" in text_lower or "no toxic" in text_lower or "avoid toxic" in text_lower or "non-toxic" in text_lower:
            excluded.update(["Pb", "Cd", "Hg"])

        # Check exclusion spans
        exclusion_patterns = [
            r"(?:without toxic elements such as|toxic elements such as)\s+([^.;]+)",
            r"(?:without|free of|excluding|exclude|avoid)\s+([^.;]+?)(?:\s+(?:with|having|for|targeting)|$|[.;])",
            r"\bno\s+([^.;]+?)(?:\s+(?:with|having|for|targeting)|$|[.;])",
            r"([A-Za-z,\s]+?)\s+(?:must be|are|should be|is)\s+(?:completely\s+|strictly\s+)?(?:excluded|prohibited|avoided|forbidden)"
        ]

        for pat in exclusion_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                span_text = m.group(1)
                found = self._find_elements_in_span(span_text)
                excluded.update(found)

        # Detect direct element symbol sequences like "no Pb Cd Hg" or "no Pb, Cd, Hg"
        direct_shorthand = re.finditer(r"\bno\s+([A-Za-z,\s]+)", text)
        for m in direct_shorthand:
            found = self._find_elements_in_span(m.group(1))
            excluded.update(found)

        return sorted(list(excluded))

    def _extract_required_elements(self, text: str, excluded: List[str]) -> List[str]:
        required = set()
        text_lower = text.lower()

        # Check for "-based" pattern: "silicon-based", "si-based", "lithium-based"
        based_matches = re.findall(r"([a-z]+|\b[A-Z][a-z]?)-based", text, re.IGNORECASE)
        for bm in based_matches:
            b_clean = bm.lower().strip()
            if b_clean in self.element_name_to_symbol:
                required.add(self.element_name_to_symbol[b_clean])
            elif bm in self.elements_dict:
                required.add(bm)

        # Check for "containing X", "with X and Y", "material with X"
        inclusion_patterns = [
            r"(?:containing|incorporating|consisting of|based on|composed of)\s+([^.,;]+)",
            r"(?:material|crystal)\s+with\s+([^.,;]+)",
            r"(?:need|looking for|want)\s+(?:a\s+)?([a-z\s]+?)\s+(?:material|crystal|structure)"
        ]

        for pat in inclusion_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                span = m.group(1)
                if any(neg in span.lower() for neg in ["without", "no ", "avoid", "free"]):
                    continue
                found = self._find_elements_in_span(span)
                for f in found:
                    if f not in excluded:
                        required.add(f)

        # General chemical words in positive context
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        for w in words:
            wl = w.lower()
            if wl in ["silicon", "lithium", "sodium", "potassium", "magnesium", "phosphorus", "sulfur", "germanium"]:
                sym = self.element_name_to_symbol[wl]
                if sym not in excluded:
                    # check it's not right after exclusion words
                    idx = text_lower.find(wl)
                    prefix = text_lower[max(0, idx - 25):idx]
                    if not any(neg in prefix for neg in ["without", "no ", "avoid", "free", "toxic"]):
                        required.add(sym)

        return sorted(list(required))

    def _find_elements_in_span(self, span: str) -> List[str]:
        results = set()
        # Look for element names & symbols
        tokens = re.findall(r"\b[a-zA-Z]+\b", span)
        for t in tokens:
            tl = t.lower()
            if tl in self.element_name_to_symbol:
                results.add(self.element_name_to_symbol[tl])
            elif t in self.elements_dict and len(t) <= 2:
                results.add(t)
        return list(results)

    def _extract_material_type(self, text: str) -> Optional[str]:
        # Check for hyphenated "-based" patterns like "sodium-based", "silicon-based"
        m = re.search(r"\b([a-zA-Z]+-based)\b", text, re.IGNORECASE)
        if m:
            return m.group(1).lower()
        if re.search(r"\bsolid\s*(?:state\s*)?electrolyte\b", text, re.IGNORECASE):
            return "solid electrolyte"
        if re.search(r"\bcathode\b", text, re.IGNORECASE):
            return "cathode"
        if re.search(r"\banode\b", text, re.IGNORECASE):
            return "anode"
        if re.search(r"\benergy\s*storage\b", text, re.IGNORECASE):
            return "energy storage"
        return None

    def _extract_band_gap(self, text: str) -> Optional[PropertyConstraint]:
        # Range: between X and Y eV or X to Y eV or X - Y eV
        range_match = re.search(
            r"band\s*gap\s*(?:of|is|between)?\s*(\d+(?:\.\d+)?)\s*(?:to|and|-)\s*(\d+(?:\.\d+)?)\s*(?:ev|electron\s*volts?)?",
            text,
            re.IGNORECASE
        )
        if range_match:
            try:
                min_val = float(range_match.group(1))
                max_val = float(range_match.group(2))
                return PropertyConstraint(
                    target=round((min_val + max_val) / 2.0, 3),
                    min=min_val,
                    max=max_val,
                    type="hard_constraint",
                    unit="eV",
                    confidence="High"
                )
            except ValueError:
                pass

        # Single target: around 2.3 eV, ~2.3 eV, 2.3 eV
        target_match = re.search(
            r"band\s*gap\s*(?:around|approx|approximately|near|of|is|~|=|:)?\s*(\d+(?:\.\d+)?)\s*(?:ev|electron\s*volts?)?",
            text,
            re.IGNORECASE
        )
        if target_match:
            try:
                val = float(target_match.group(1))
                return PropertyConstraint(
                    target=val,
                    tolerance=0.3,
                    type="hard_constraint",
                    unit="eV",
                    confidence="High"
                )
            except ValueError:
                pass

        return None

    def _extract_energy_above_hull(self, text: str) -> Optional[PropertyConstraint]:
        # 1. Numerical constraint (must contain explicit digits)
        num_match = re.search(
            r"(?:energy\s*above\s*hull|e_hull|ehull)\s*(?:below|less\s*than|under|<=|<|=|~)?\s*(\d+(?:\.\d+)?)\s*(?:ev\/atom|ev\s*per\s*atom|ev)",
            text,
            re.IGNORECASE
        ) or re.search(
            r"(?:energy\s*above\s*hull|e_hull|ehull)\s*(?:below|less\s*than|under|<=|<)\s*(\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        if num_match:
            try:
                val = float(num_match.group(1))
                return PropertyConstraint(
                    max=val,
                    target=val,
                    type="hard_constraint",
                    unit="eV/atom",
                    preference="low",
                    confidence="High"
                )
            except ValueError:
                pass

        # 2. Qualitative preference: "low energy above hull"
        if re.search(r"\blow\s*(?:energy\s*above\s*hull|hull\s*energy)\b", text, re.IGNORECASE) or \
           re.search(r"\b(?:energy\s*above\s*hull|hull\s*energy)\s*(?:is\s*)?low\b", text, re.IGNORECASE):
            return PropertyConstraint(
                target=None,
                max=None,
                type="soft_preference",
                preference="low",
                unit="eV/atom",
                confidence="High"
            )

        # 3. Qualitative: "stable" or "high stability"
        if re.search(r"\b(stable|stability)\b", text, re.IGNORECASE):
            return PropertyConstraint(
                target=None,
                max=None,
                type="soft_preference",
                preference="stable",
                unit="eV/atom",
                confidence="Medium"
            )

        return None

    def _extract_ionic_conductivity(self, text: str) -> Optional[PropertyConstraint]:
        # 1. Qualitative check first: "high ionic conductivity", "fast ion conduction", etc.
        if re.search(r"\b(high|fast|good|superionic|elevated)\s*(?:ionic\s*conductivity|ion\s*conduction)\b", text, re.IGNORECASE) or \
           re.search(r"\b(?:ionic\s*conductivity|ion\s*conduction)\s*(?:is\s*)?(?:high|fast|good)\b", text, re.IGNORECASE):
            return PropertyConstraint(
                target=None,
                min=None,
                type="soft_preference",
                preference="high",
                unit="S/cm",
                confidence="High"
            )

        # 2. Numerical constraint (must contain explicit digits \d+)
        num_match = re.search(
            r"ionic\s*conductivity\s*(?:above|greater\s*than|>=|>|of|is|=|~)?\s*(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*(?:s\/cm|ms\/cm)",
            text,
            re.IGNORECASE
        ) or re.search(
            r"ionic\s*conductivity\s*(?:above|greater\s*than|>=|>)\s*(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)",
            text,
            re.IGNORECASE
        )
        if num_match:
            try:
                val = float(num_match.group(1))
                return PropertyConstraint(
                    target=val,
                    min=val,
                    type="hard_constraint",
                    unit="S/cm",
                    preference="high",
                    confidence="High"
                )
            except ValueError:
                pass

        # 3. Generic mention without qualifiers
        if re.search(r"\b(?:ionic\s*conductivity|ion\s*conduction)\b", text, re.IGNORECASE):
            return PropertyConstraint(
                target=None,
                min=None,
                type="soft_preference",
                preference="high",
                unit="S/cm",
                confidence="Medium"
            )

        return None

    def _extract_capacity(self, text: str) -> Optional[PropertyConstraint]:
        # 1. Qualitative check first: "high capacity", "large capacity"
        if re.search(r"\b(high|large|superior|maximum|good)\s+capacity\b", text, re.IGNORECASE) or \
           re.search(r"\bhigh-capacity\b", text, re.IGNORECASE) or \
           re.search(r"\bcapacity\s*(?:is\s*)?(?:high|large)\b", text, re.IGNORECASE):
            return PropertyConstraint(
                target=None,
                min=None,
                type="soft_preference",
                preference="high",
                confidence="High",
                unit="mAh/g"
            )

        # 2. Numerical constraint
        num_match = re.search(
            r"capacity\s*(?:above|greater\s*than|>=|>|of|is|=|~)?\s*(\d+(?:\.\d+)?)\s*(?:mah\/g)",
            text,
            re.IGNORECASE
        ) or re.search(
            r"capacity\s*(?:above|greater\s*than|>=|>)\s*(\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE
        )
        if num_match:
            try:
                val = float(num_match.group(1))
                return PropertyConstraint(
                    target=val,
                    min=val,
                    type="hard_constraint",
                    unit="mAh/g",
                    preference="high",
                    confidence="High"
                )
            except ValueError:
                pass

        return None

    def _extract_volume_change(self, text: str) -> Optional[PropertyConstraint]:
        # 1. Numerical constraint
        num_match = re.search(
            r"(?:less\s*than|below|under|<=|<)?\s*(\d+(?:\.\d+)?)\s*%\s*(?:volume\s*change|volume\s*expansion)",
            text,
            re.IGNORECASE
        ) or re.search(
            r"(?:volume\s*change|volume\s*expansion)\s*(?:less\s*than|below|under|<=|<)?\s*(\d+(?:\.\d+)?)\s*%",
            text,
            re.IGNORECASE
        )
        if num_match:
            try:
                val = float(num_match.group(1))
                return PropertyConstraint(
                    target=val,
                    max=val,
                    type="hard_constraint",
                    unit="%",
                    preference="low",
                    confidence="High"
                )
            except ValueError:
                pass

        # 2. Qualitative preference
        if re.search(r"\b(low|minimal|small)\s+(?:volume\s*change|volume\s*expansion)\b", text, re.IGNORECASE):
            return PropertyConstraint(
                target=None,
                max=None,
                type="soft_preference",
                preference="low",
                confidence="High",
                unit="%"
            )

        return None

    @staticmethod
    def clean_and_parse_llm_json(raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Safely strips markdown code blocks (```json ... ```) and parses structured JSON output from LLMs.
        Returns parsed dictionary or None if parsing fails.
        """
        if not raw_text or not raw_text.strip():
            return None
        text = raw_text.strip()
        # Strip ```json ... ``` or ``` ... ```
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        # Find JSON object
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        try:
            return json.loads(text)
        except Exception:
            return None
