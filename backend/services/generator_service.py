"""
Crystal Generator Interface and Dispatch Service for CRYSTAL-X.
Defines the common generator contract and manages REAL_GENERATOR (MatterGen)
vs DEMO_GENERATOR modes based on environment configuration.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from pymatgen.core import Structure
from backend.models.schemas import MaterialRequirements


class CrystalGenerator(ABC):
    @abstractmethod
    def generate(self, requirements: MaterialRequirements, num_candidates: int) -> List[Dict[str, Any]]:
        """
        Generates candidate crystal structures based on the input constraints.
        Returns a list of dicts with keys:
        - raw_cif: str
        - structure: Structure
        - generator_name: str
        - generation_source: str ("MATTERGEN" or "LOCAL_DEMO")
        - generation_mode: str ("REAL_GENERATOR" or "DEMO_GENERATOR")
        - configured_model: str
        - seed_info: Optional[int]
        - metadata: Dict[str, Any]
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_mode_name(self) -> str:
        pass


class GeneratorDispatchService:
    def __init__(self, demo_generator: CrystalGenerator, mattergen_adapter: CrystalGenerator):
        self.demo_gen = demo_generator
        self.mattergen_gen = mattergen_adapter

    def get_active_generator(
        self,
        requested_mode: Optional[str] = None,
        configured_model: Optional[str] = None
    ) -> Tuple[CrystalGenerator, str, str, str]:
        """
        Returns (generator_instance, mode_name, configured_model_name, notice_message).
        """
        model_name = configured_model or getattr(self.mattergen_gen, "configured_model", "MATTERGEN_PROPERTY_CONDITIONED")

        if requested_mode == "mattergen":
            if self.mattergen_gen.is_available():
                return self.mattergen_gen, "REAL_GENERATOR", model_name, f"MatterGen generative diffusion active ({model_name})."
            else:
                return self.demo_gen, "DEMO_GENERATOR", "LOCAL_DEMO", "MatterGen requested but unavailable in this environment. Fell back to DEMO GENERATION MODE."

        if self.mattergen_gen.is_available():
            return self.mattergen_gen, "REAL_GENERATOR", model_name, f"MatterGen generative diffusion active ({model_name})."

        return self.demo_gen, "DEMO_GENERATOR", "LOCAL_DEMO", "DEMO GENERATION MODE — candidates are prototype-generated and not equivalent to MatterGen output."
