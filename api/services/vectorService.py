import asyncio
from typing import List

from sentence_transformers import SentenceTransformer
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from core.config import settings
from schemas.documents import DocumentBase


class VectorService:
    def __init__(self):
        self.collection_name = settings.qdrant_collection
        self.client = AsyncQdrantClient(
            url=f"http://{settings.qdrant_host}:{settings.qdrant_port}",
            api_key=settings.qdrant_api_key,
        )
        # Lazy initialization of embedder
        self._embedder = None
        self._vector_size = None
        self._collection_ready = False
        self._collection_lock = asyncio.Lock()
        self._embedder_lock = asyncio.Lock()

    def _get_embedder(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._embedder is None:
            self._embedder = SentenceTransformer(settings.vector_model_name)
            self._vector_size = self._embedder.get_sentence_embedding_dimension()
        return self._embedder

    @property
    def vector_size(self) -> int:
        """Get vector size, initializing embedder if needed."""
        if self._vector_size is None:
            self._get_embedder()
        return self._vector_size

    async def _ensure_collection(self) -> None:
        if self._collection_ready:
            return

        async with self._collection_lock:
            if self._collection_ready:
                return
            try:
                await self.client.get_collection(collection_name=self.collection_name)
            except Exception:
                await self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
            self._collection_ready = True

    async def _embed(self, text: str) -> List[float]:
        # SentenceTransformer encode is synchronous; run in a worker thread
        embedder = self._get_embedder()
        return await asyncio.to_thread(lambda: embedder.encode(text).tolist())

    async def upsert_document(self, document: DocumentBase) -> None:
        await self._ensure_collection()
        vector = await self._embed(f"{document.title}\n{document.content}")
        payload = document.model_dump(mode="json")
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                qmodels.PointStruct(
                    id=document.id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    async def delete_document(self, document_id: str) -> None:
        await self._ensure_collection()
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.PointIdsList(points=[document_id]),
        )

    async def search(self, query: str, limit: int) -> list[qmodels.ScoredPoint]:
        await self._ensure_collection()
        vector = await self._embed(query)
        return await self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )


vector_service = VectorService()
