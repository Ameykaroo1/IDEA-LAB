"""
Vector Store & Embedding Service for CRYSTAL-X RAG Scientific Validation.
Manages persistent embeddings, document chunks, and similarity search.
Uses ChromaDB with a robust, zero-network scientific embedding function and
an automatic in-memory fallback.
"""

import os
import json
import math
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from backend.models.rag_schemas import DocumentChunk


class ScientificEmbeddingFunction:
    """
    Deterministic, offline-safe scientific embedding function.
    Combines subword n-grams, chemical element tokens, and domain keyword frequencies
    into a unit-normalized dense vector representation.
    Ensures 100% offline operation, zero network calls, and instant test execution.
    """
    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        # Core domain keywords for materials science energy applications
        self.keywords = [
            "electrolyte", "battery", "lithium", "sodium", "ionic", "conductivity",
            "stability", "hull", "convex", "formation", "energy", "electrode",
            "cathode", "anode", "garnet", "thiophosphate", "nasicon", "halide",
            "perovskite", "olivine", "activation", "migration", "barrier", "diffusivity",
            "impedance", "synthesizability", "decomposition", "moisture", "dendrite",
            "interfacial", "redox", "capacity", "voltage", "bandgap", "cif", "lattice"
        ]

    def _hash_token(self, token: str) -> int:
        return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dimension

    def embed_text(self, text: str) -> List[float]:
        vec = np.zeros(self.dimension, dtype=np.float32)
        text_lower = text.lower()
        words = re.findall(r"[a-z0-9_]+", text_lower)
        
        # 1. Domain keyword weighting
        for idx, kw in enumerate(self.keywords):
            count = text_lower.count(kw)
            if count > 0:
                pos = (idx * 3) % self.dimension
                vec[pos] += math.log1p(count) * 2.5

        # 2. Chemical formulas and capitalized element symbols
        chem_tokens = re.findall(r"\b[A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*)*\b", text)
        for tok in chem_tokens:
            h = self._hash_token(tok)
            vec[h] += 3.0

        # 3. Word hashing
        for w in words:
            h = self._hash_token(w)
            vec[h] += 1.0

        # 4. Trigram feature hashing
        for i in range(max(0, len(text_lower) - 3)):
            tri = text_lower[i:i+3]
            h = self._hash_token(tri)
            vec[h] += 0.15

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec.tolist()

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in input]


class RAGVectorStore:
    def __init__(self, storage_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if not storage_dir:
            storage_dir = os.path.join(base_dir, "data", "rag_storage")
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.index_file = os.path.join(storage_dir, "chunks_index.json")

        self.embedder = ScientificEmbeddingFunction(dimension=128)
        self._chunks: Dict[str, DocumentChunk] = {}
        self._embeddings: Dict[str, List[float]] = {}
        self._chroma_collection = None

        self._init_chroma()
        self._load_local_index()

    def _init_chroma(self):
        try:
            import chromadb
            from chromadb.config import Settings
            from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

            class ScientificChromaEmbeddingAdapter(EmbeddingFunction):
                def __init__(self, embed_fn):
                    self.embed_fn = embed_fn

                def name(self) -> str:
                    return "scientific_domain_embedding"

                def __call__(self, input: Documents) -> Embeddings:
                    return [self.embed_fn.embed_text(doc) for doc in input]

            settings = Settings(anonymized_telemetry=False, is_persistent=False)
            client = chromadb.Client(settings=settings)
            adapter = ScientificChromaEmbeddingAdapter(self.embedder)

            self._chroma_collection = client.create_collection(
                name="crystal_x_scientific_literature",
                embedding_function=adapter,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            # Automatic graceful fallback to internal memory/json index
            self._chroma_collection = None

    def _load_local_index(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("chunks", []):
                        chunk = DocumentChunk(**item)
                        self._chunks[chunk.chunk_id] = chunk
                        self._embeddings[chunk.chunk_id] = self.embedder.embed_text(chunk.content)
            except Exception:
                pass

    def _save_local_index(self):
        try:
            data = {
                "total_chunks": len(self._chunks),
                "chunks": [c.model_dump() for c in self._chunks.values()]
            }
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def add_chunks(self, chunks: List[DocumentChunk]):
        if not chunks:
            return

        texts = []
        ids = []
        metas = []
        embeddings = []

        for c in chunks:
            self._chunks[c.chunk_id] = c
            emb = self.embedder.embed_text(c.content)
            self._embeddings[c.chunk_id] = emb

            texts.append(c.content)
            ids.append(c.chunk_id)
            embeddings.append(emb)
            metas.append({
                "document_id": c.document_id,
                "title": c.title[:100],
                "year": c.publication_year or 0,
                "source_type": c.source_type,
                "page": c.page_number or 1,
                "formulas": ",".join(c.formulas_mentioned[:8])
            })

        # Insert to Chroma if active
        if self._chroma_collection is not None:
            try:
                self._chroma_collection.upsert(
                    ids=ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metas
                )
            except Exception:
                pass

        self._save_local_index()

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        return self._chunks.get(chunk_id)

    def get_all_chunks(self) -> List[DocumentChunk]:
        return list(self._chunks.values())

    def get_all_documents(self) -> List[Dict[str, Any]]:
        docs: Dict[str, Dict[str, Any]] = {}
        for c in self._chunks.values():
            if c.document_id not in docs:
                docs[c.document_id] = {
                    "document_id": c.document_id,
                    "title": c.title,
                    "authors": c.authors,
                    "publication_year": c.publication_year,
                    "doi_or_url": c.doi_or_url,
                    "source_type": c.source_type,
                    "chunk_count": 0,
                    "formulas_mentioned": set()
                }
            docs[c.document_id]["chunk_count"] += 1
            docs[c.document_id]["formulas_mentioned"].update(c.formulas_mentioned)

        res = []
        for d in docs.values():
            d["formulas_mentioned"] = list(d["formulas_mentioned"])
            res.append(d)
        return res

    def search_similar(
        self,
        query: str,
        top_k: int = 8,
        filter_source: Optional[str] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Cosine similarity vector search over embedded chunks.
        Returns list of (DocumentChunk, similarity_score).
        """
        if not self._chunks:
            return []

        q_vec = np.array(self.embedder.embed_text(query), dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-6:
            return []

        results = []
        for cid, c in self._chunks.items():
            if filter_source and c.source_type != filter_source:
                continue

            c_vec = np.array(self._embeddings.get(cid, []), dtype=np.float32)
            if len(c_vec) != len(q_vec):
                continue
            
            c_norm = np.linalg.norm(c_vec)
            if c_norm < 1e-6:
                sim = 0.0
            else:
                sim = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
                sim = max(0.0, min(1.0, (sim + 1.0) / 2.0))  # Map [-1, 1] to [0, 1]

            results.append((c, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def clear(self):
        self._chunks.clear()
        self._embeddings.clear()
        if os.path.exists(self.index_file):
            try:
                os.remove(self.index_file)
            except Exception:
                pass
