"""Qdrant vector store adapter."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class VectorMatch:
    """Near-duplicate vector match."""

    record_id: int
    score: float


class VectorStore(Protocol):
    """Protocol for duplicate detector vector store adapters."""

    async def upsert_resume_vector(
        self,
        *,
        record_id: int,
        telegram_user_id: int,
        vector: list[float],
    ) -> None:
        """Persist a resume vector."""

    async def search_similar(
        self,
        *,
        telegram_user_id: int,
        vector: list[float],
        limit: int,
        threshold: float,
    ) -> list[VectorMatch]:
        """Search same-user resume vectors."""


class QdrantVectorStore:
    """Small Qdrant adapter kept behind a stable app interface."""

    def __init__(
        self,
        *,
        url: str,
        collection: str,
        vector_size: int,
    ) -> None:
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=url)
        self.collection = collection
        self.vector_size = vector_size

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection when it does not already exist."""

        from qdrant_client import models

        if not self._client.collection_exists(self.collection):
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    async def upsert_resume_vector(
        self,
        *,
        record_id: int,
        telegram_user_id: int,
        vector: list[float],
    ) -> None:
        """Upsert a resume vector into Qdrant."""

        from qdrant_client import models

        self._client.upsert(
            collection_name=self.collection,
            points=[
                models.PointStruct(
                    id=record_id,
                    vector=vector,
                    payload={
                        "record_id": record_id,
                        "telegram_user_id": telegram_user_id,
                    },
                )
            ],
        )

    async def search_similar(
        self,
        *,
        telegram_user_id: int,
        vector: list[float],
        limit: int = 1,
        threshold: float = 0.88,
    ) -> list[VectorMatch]:
        """Search for same-user near duplicates in Qdrant."""

        from qdrant_client import models

        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="telegram_user_id",
                    match=models.MatchValue(value=telegram_user_id),
                )
            ]
        )
        raw_matches: list[Any]
        if hasattr(self._client, "query_points"):
            result = self._client.query_points(
                collection_name=self.collection,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=threshold,
            )
            raw_matches = list(result.points)
        else:  # pragma: no cover - compatibility for older qdrant-client versions
            raw_matches = self._client.search(
                collection_name=self.collection,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=threshold,
            )

        return [
            VectorMatch(record_id=int(match.payload["record_id"]), score=float(match.score))
            for match in raw_matches
            if getattr(match, "payload", None) and "record_id" in match.payload
        ]
