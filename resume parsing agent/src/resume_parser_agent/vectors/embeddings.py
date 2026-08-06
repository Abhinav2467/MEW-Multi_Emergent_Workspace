"""Local embedding generation."""

from typing import Protocol


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingProvider(Protocol):
    """Protocol for testable embedding providers."""

    def embed_text(self, text: str) -> list[float]:
        """Return one embedding vector for text."""


class LocalEmbeddingProvider:
    """Lazy sentence-transformers embedding provider."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model: object | None = None

    def embed_text(self, text: str) -> list[float]:
        """Embed text with a local sentence-transformers model."""

        model = self._load_model()
        vector = model.encode([text], normalize_embeddings=True)[0]
        return [float(value) for value in vector]

    def _load_model(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model
