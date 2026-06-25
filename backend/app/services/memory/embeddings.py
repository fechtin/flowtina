"""Embedding providers for semantic memory search.

Hidden behind a small interface so the backend is swappable without touching the
memory pipeline (per the architecture's portability goal):

* ``hash``      — dependency-free feature-hash embedding. Deterministic, offline,
  captures lexical overlap; good enough for dedupe and coarse recall on a tiny VM.
* ``gemini``    — Google ``text-embedding-004`` (multilingual) via API, truncated
  to the configured dimension. Zero local RAM cost.
* ``model2vec`` — local open-source static embeddings; lazily imported so the
  dependency is optional. Falls back to ``hash`` if the package is unavailable.

All providers return L2-normalized vectors, so cosine similarity reduces to a dot
product.
"""

from __future__ import annotations

import hashlib
import math
import re

import httpx

from app.core.config import settings
from app.core.logger import get_logger

log = get_logger("ai")

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors (0.0 if either is empty)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingProvider:
    """Abstract embedding backend. Implementations override :meth:`embed`."""

    name: str = "base"

    def __init__(self, dim: int) -> None:
        self.dim = dim

    async def embed(self, text: str) -> list[float]:  # pragma: no cover - interface
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Signed feature-hashing (the "hashing trick") over unigrams + bigrams.

    Tokens that two texts share map to the same buckets, so semantically similar
    phrasings land close in vector space. Fully deterministic and offline.
    """

    name = "hash"

    def _bucket(self, token: str) -> tuple[int, float]:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:6], "big") % self.dim
        sign = 1.0 if digest[7] & 1 else -1.0
        return idx, sign

    async def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = _tokens(text)
        features = list(tokens)
        features += [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            idx, sign = self._bucket(feature)
            vector[idx] += sign
        return _normalize(vector)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google ``text-embedding-004`` via the Generative Language API."""

    name = "gemini"
    _ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, dim: int, model: str, api_key: str) -> None:
        super().__init__(dim)
        self.model = model or "text-embedding-004"
        self.api_key = api_key

    async def embed(self, text: str) -> list[float]:
        url = f"{self._ENDPOINT}/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text or ""}]},
            "outputDimensionality": self.dim,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"Gemini embedding HTTP {resp.status_code}: {resp.text[:200]}")
        values = (resp.json().get("embedding") or {}).get("values") or []
        return _normalize([float(v) for v in values])


class Model2VecEmbeddingProvider(EmbeddingProvider):
    """Local open-source static embeddings via the optional ``model2vec`` package."""

    name = "model2vec"

    def __init__(self, model: str) -> None:
        from model2vec import StaticModel  # type: ignore[import-not-found]  # optional dep

        self._model = StaticModel.from_pretrained(model)
        super().__init__(int(self._model.dim))

    async def embed(self, text: str) -> list[float]:
        vector = self._model.encode([text or ""])[0]
        return _normalize([float(v) for v in vector.tolist()])


def get_embedding_provider() -> EmbeddingProvider:
    """Build the configured embedding backend, falling back to hash on failure."""
    backend = (settings.memory_embedding_provider or "hash").lower()
    dim = settings.memory_embedding_dim

    if backend == "gemini":
        api_key = settings.gemini_api_key
        if api_key:
            return GeminiEmbeddingProvider(dim, settings.memory_embedding_model, api_key)
        log.warning("memory: gemini embedding selected but no gemini_api_key; using hash")
    elif backend == "model2vec":
        try:
            return Model2VecEmbeddingProvider(settings.memory_embedding_model)
        except Exception as exc:  # noqa: BLE001 - optional dep / download failure
            log.warning(f"memory: model2vec unavailable ({exc}); using hash")

    return HashEmbeddingProvider(dim)
