"""Embedding protocol and deterministic test embedding client."""

import hashlib
import math
import re
from typing import Protocol


class EmbeddingClientProtocol(Protocol):
    """Protocol for embedding text."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per text."""
        ...


class DeterministicEmbeddingClient:
    """Hashing bag-of-words embedding client with no external dependency."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed text into deterministic normalized vectors."""
        vectors = [self._embed_one(text) for text in texts]
        return vectors

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[\w]+", text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Return cosine similarity for two equal-length vectors."""
    return sum(a * b for a, b in zip(left, right, strict=False))
