"""
External Scientific Data Connectors for CRYSTAL-X RAG.
Interfaces with:
1. Materials Project (MP API v2) - requires MP_API_KEY
2. Crystallography Open Database (COD REST API) - public, no key
3. Local Reference Catalog (MP-20 & JARVIS-DFT) - local SQLite
Handles missing credentials, timeouts, and network unavailability safely.
"""

import os
import json
import sqlite3
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional


class MaterialsProjectConnector:
    """
    Official documented Materials Project API connector.
    Reads MP_API_KEY from environment variables.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MP_API_KEY")
        self.base_url = "https://api.materialsproject.org"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "YOUR_MP_API_KEY_HERE")

    def lookup_formula(self, formula: str, limit: int = 3) -> Dict[str, Any]:
        """
        Queries Materials Project for crystal materials matching the chemical formula.
        Returns structured computed DFT properties and provenance.
        """
        if not self.is_configured():
            return {
                "source": "Materials Project",
                "status": "NOT_CONFIGURED",
                "message": "Materials Project API key is not configured. Add MP_API_KEY to your .env file to enable live MP queries.",
                "records": []
            }

        try:
            url = f"{self.base_url}/materials/summary/?formula={urllib.parse.quote(formula)}&_limit={limit}"
            req = urllib.request.Request(
                url,
                headers={
                    "X-API-KEY": self.api_key,
                    "User-Agent": "CRYSTAL-X-Research-Platform/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                records = []
                for item in data.get("data", []):
                    records.append({
                        "mp_id": item.get("material_id"),
                        "formula": item.get("formula_pretty"),
                        "symmetry": item.get("symmetry", {}).get("symbol"),
                        "energy_above_hull": item.get("energy_above_hull"),
                        "band_gap": item.get("band_gap"),
                        "formation_energy": item.get("formation_energy_per_atom"),
                        "is_stable": item.get("is_stable"),
                        "calculation_method": "GGA+U DFT (VASP PBEsol)",
                        "property_provenance": "DATABASE_COMPUTED"
                    })
                return {
                    "source": "Materials Project",
                    "status": "SUCCESS",
                    "count": len(records),
                    "records": records
                }
        except Exception as e:
            return {
                "source": "Materials Project",
                "status": "UNAVAILABLE",
                "message": f"External Materials Project lookup failed or timed out: {str(e)}",
                "records": []
            }


class CrystallographyOpenDatabaseConnector:
    """
    Crystallography Open Database (COD) REST API connector.
    Open-access crystallographic database containing experimental crystal structures.
    Controlled via ENABLE_COD_API environment variable to prevent network stalls when offline.
    """
    def __init__(self):
        self.base_url = "https://www.crystallography.net/cod/result"
        self.enabled = os.getenv("ENABLE_COD_API", "false").lower() in ("1", "true", "yes")

    def lookup_formula(self, formula: str, limit: int = 3) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "source": "Crystallography Open Database (COD)",
                "status": "DISABLED_OFFLINE (Set ENABLE_COD_API=1 in .env to query live COD)",
                "message": "COD live API disabled by default to maintain fast offline operation.",
                "records": []
            }

        try:
            params = urllib.parse.urlencode({
                "format": "json",
                "formula": formula
            })
            url = f"{self.base_url}?{params}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CRYSTAL-X-Platform/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                records = []
                for row in data[:limit]:
                    records.append({
                        "cod_id": row.get("file"),
                        "formula": row.get("formula"),
                        "space_group": row.get("sg"),
                        "cell_a": row.get("a"),
                        "cell_b": row.get("b"),
                        "cell_c": row.get("c"),
                        "authors": row.get("authors"),
                        "title": row.get("title"),
                        "journal": row.get("journal"),
                        "year": row.get("year"),
                        "property_provenance": "EXPERIMENTAL_CRYSTALLOGRAPHY"
                    })
                return {
                    "source": "Crystallography Open Database (COD)",
                    "status": "SUCCESS",
                    "count": len(records),
                    "records": records
                }
        except Exception as e:
            return {
                "source": "Crystallography Open Database (COD)",
                "status": "OFFLINE_OR_UNAVAILABLE",
                "message": f"COD network lookup unavailable: {str(e)}",
                "records": []
            }


class LocalCatalogConnector:
    """
    Local High-Fidelity Catalog Connector (MP-20 and JARVIS-DFT).
    Always available offline from data/reference_catalog.db.
    """
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            db_path = os.path.join(base_dir, "data", "reference_catalog.db")
        self.db_path = db_path

    def lookup_formula_and_system(self, formula: str, chemical_system: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        if not os.path.exists(self.db_path):
            return {
                "source": "Local Reference Catalog (MP-20 / JARVIS)",
                "status": "DB_NOT_FOUND",
                "records": []
            }

        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            records = []
            # 1. Exact formula query
            cur.execute("""
                SELECT material_id, dataset_source, dataset_split, formula, reduced_formula,
                       chemical_system, crystal_system, space_group, formation_energy_per_atom,
                       energy_above_hull, band_gap, density
                FROM reference_materials
                WHERE formula = ? OR reduced_formula = ?
                LIMIT ?
            """, (formula, formula, limit))
            for r in cur.fetchall():
                records.append({
                    "material_id": r["material_id"],
                    "dataset_source": r["dataset_source"],
                    "formula": r["formula"],
                    "reduced_formula": r["reduced_formula"],
                    "crystal_system": r["crystal_system"],
                    "space_group": r["space_group"],
                    "energy_above_hull": r["energy_above_hull"],
                    "formation_energy": r["formation_energy_per_atom"],
                    "band_gap": r["band_gap"],
                    "match_type": "EXACT_FORMULA_MATCH",
                    "provenance": f"COMPUTED_DATABASE_{r['dataset_source']}"
                })

            # 2. Chemical system analogs if under limit
            if len(records) < limit and chemical_system:
                needed = limit - len(records)
                cur.execute("""
                    SELECT material_id, dataset_source, dataset_split, formula, reduced_formula,
                           chemical_system, crystal_system, space_group, formation_energy_per_atom,
                           energy_above_hull, band_gap, density
                    FROM reference_materials
                    WHERE chemical_system = ? AND formula != ?
                    ORDER BY CASE WHEN energy_above_hull IS NULL THEN 1 ELSE 0 END, energy_above_hull ASC
                    LIMIT ?
                """, (chemical_system, formula, needed))
                for r in cur.fetchall():
                    records.append({
                        "material_id": r["material_id"],
                        "dataset_source": r["dataset_source"],
                        "formula": r["formula"],
                        "reduced_formula": r["reduced_formula"],
                        "crystal_system": r["crystal_system"],
                        "space_group": r["space_group"],
                        "energy_above_hull": r["energy_above_hull"],
                        "formation_energy": r["formation_energy_per_atom"],
                        "band_gap": r["band_gap"],
                        "match_type": "CHEMICAL_SYSTEM_ANALOG",
                        "provenance": f"COMPUTED_DATABASE_{r['dataset_source']}"
                    })

            conn.close()
            return {
                "source": "Local Reference Catalog (MP-20 / JARVIS-DFT)",
                "status": "SUCCESS",
                "count": len(records),
                "records": records
            }
        except Exception as e:
            return {
                "source": "Local Reference Catalog",
                "status": "ERROR",
                "message": str(e),
                "records": []
            }
