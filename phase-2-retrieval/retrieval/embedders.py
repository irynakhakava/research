"""Embedders: sentence-transformers (prod) и hash (tests / offline smoke)."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Sequence

import numpy as np


class Embedder(ABC):
    model_name: str

    @abstractmethod
    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        """Вернуть матрицу (N, dim), L2-normalized если так задумано."""

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        return self.embed_passages(texts)

    @property
    @abstractmethod
    def dim(self) -> int: ...


class HashEmbedder(Embedder):
    """Детерминированный псевдо-эмбеддинг для unit-тестов без сети."""

    def __init__(self, dim: int = 64, normalize: bool = True) -> None:
        self.model_name = f"hash-embedder-d{dim}"
        self._dim = dim
        self._normalize = normalize

    @property
    def dim(self) -> int:
        return self._dim

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self._dim), dtype=np.float32)
        for i, text in enumerate(texts):
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            # expand digest to dim floats in [-1, 1]
            raw = np.frombuffer((digest * ((self._dim // 32) + 1))[: self._dim * 4], dtype=np.uint8)
            # safer construction:
            rng_seed = int.from_bytes(digest[:8], "little") % (2**32)
            rng = np.random.default_rng(rng_seed)
            vectors[i] = rng.standard_normal(self._dim).astype(np.float32)
            _ = raw  # keep digest used
        if self._normalize:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-12)
            vectors = vectors / norms
        return vectors


class SentenceTransformersEmbedder(Embedder):
    """intfloat/multilingual-e5-* через sentence-transformers."""

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        *,
        batch_size: int = 16,
        normalize: bool = True,
        passage_prefix: str = "passage: ",
        query_prefix: str = "query: ",
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._batch_size = batch_size
        self._normalize = normalize
        self._passage_prefix = passage_prefix
        self._query_prefix = query_prefix
        self._model = SentenceTransformer(model_name)
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        return self._dim

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        prefixed = [self._passage_prefix + t for t in texts]
        vectors = self._model.encode(
            list(prefixed),
            batch_size=self._batch_size,
            normalize_embeddings=self._normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        prefixed = [self._query_prefix + t for t in texts]
        vectors = self._model.encode(
            list(prefixed),
            batch_size=self._batch_size,
            normalize_embeddings=self._normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)


def create_embedder(cfg: dict) -> Embedder:
    backend = str(cfg.get("backend", "sentence_transformers"))
    if backend == "hash":
        return HashEmbedder(dim=64, normalize=bool(cfg.get("normalize", True)))
    if backend in {"sentence_transformers", "st"}:
        return SentenceTransformersEmbedder(
            model_name=str(cfg.get("model_name", "intfloat/multilingual-e5-small")),
            batch_size=int(cfg.get("batch_size", 16)),
            normalize=bool(cfg.get("normalize", True)),
            passage_prefix=str(cfg.get("passage_prefix", "passage: ")),
            query_prefix=str(cfg.get("query_prefix", "query: ")),
        )
    raise ValueError(f"Unknown embeddings backend: {backend}")
