import asyncio
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from elasticsearch.exceptions import (
    NotFoundError,
    ConnectionError,
    RequestError,
    ApiError,
)
from schemas.documents import (
    DocumentBase,
    DocumentResponse,
    DocumentUpdate,
    SearchQuery,
    SearchResponse,
)
from db.es_client import es_client
from core.config import settings
from services.vectorService import vector_service


logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self):
        self.index_name = settings.documents_index
        self.client = es_client.get_async_client()
        self.vector_service = vector_service if settings.vector_search_enabled else None

    async def create_index(self) -> bool:
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "content": {"type": "text", "analyzer": "standard"},
                    "author": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        }

        try:
            if not await self.client.indices.exists(index=self.index_name):
                await self.client.indices.create(index=self.index_name, body=mapping)
                return True
            return False
        except (NotFoundError, ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Failed to create index: {e}")

    async def create_document(self, document: DocumentBase) -> DocumentBase:

        try:
            await self.client.index(
                index=self.index_name,
                id=str(document.id),
                document=document.model_dump(),
                refresh=True,
            )
            if self.vector_service:
                try:
                    await self.vector_service.upsert_document(document)
                except Exception as vector_err:
                    logger.warning(
                        "Vector upsert failed for %s: %s", document.id, vector_err
                    )
            return document
        except (NotFoundError, ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Failed to create document: {e}")

    async def get_document(self, document_id: UUID) -> Optional[DocumentBase]:
        try:
            response = await self.client.get(index=self.index_name, id=str(document_id))
            return DocumentBase(**response["_source"])
        except NotFoundError:
            return None
        except (ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Failed to get document: {e}")

    async def update_document(
        self, document_id: UUID, update_data: DocumentUpdate
    ) -> DocumentBase | None:
        current_doc = await self.get_document(document_id)
        if not current_doc:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(current_doc, field, value)

        current_doc.updated_at = datetime.now()

        try:
            await self.client.index(
                index=self.index_name,
                id=str(document_id),
                document=current_doc.model_dump(),
                refresh=True,
            )
            if self.vector_service:
                try:
                    await self.vector_service.upsert_document(current_doc)
                except Exception as vector_err:
                    logger.warning(
                        "Vector update failed for %s: %s", document_id, vector_err
                    )
            return current_doc
        except (NotFoundError, ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Failed to update document: {e}")

    async def delete_document(self, document_id: UUID) -> bool:
        try:
            response = await self.client.delete(
                index=self.index_name, id=str(document_id)
            )
            deleted = response["result"] == "deleted"
            if deleted and self.vector_service:
                try:
                    await self.vector_service.delete_document(str(document_id))
                except Exception as vector_err:
                    logger.warning(
                        "Vector delete failed for %s: %s", document_id, vector_err
                    )
            return deleted
        except NotFoundError:
            return False
        except RequestError as e:
            if (
                hasattr(e, "meta")
                and hasattr(e.meta, "status")
                and e.meta.status == 404
            ):
                return False
            raise Exception(f"Failed to delete document: {e}")
        except (ConnectionError, ApiError) as e:
            raise Exception(f"Failed to delete document: {e}")

    def _build_es_query(self, search_query: SearchQuery) -> Dict[str, Any]:
        default_fields = ["title^3", "content^2", "author^2", "tags^2"]
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": search_query.query,
                                "fields": default_fields,
                                "fuzziness": "AUTO",
                                "operator": "or",
                                "type": "best_fields",
                            }
                        },
                        {"wildcard": {"content": f"*{search_query.query}*"}},
                        {"wildcard": {"title": f"*{search_query.query}*"}},
                    ]
                }
            },
            "size": search_query.size,
            "from": search_query.from_,
        }

    async def _search_elasticsearch(
        self, search_query: SearchQuery
    ) -> tuple[int, List[DocumentResponse], int]:
        query_body = self._build_es_query(search_query)
        try:
            response = await self.client.search(index=self.index_name, body=query_body)
            hits = response["hits"]["hits"]
            results = [DocumentResponse(**hit["_source"]) for hit in hits]
            total = response["hits"]["total"]["value"]
            return total, results, response["took"]
        except (NotFoundError, ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Search failed: {e}")

    async def _search_vector(self, search_query: SearchQuery) -> List[DocumentResponse]:
        if not self.vector_service:
            return []

        try:
            hits = await self.vector_service.search(
                search_query.query, search_query.size
            )
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            return []

        results: List[DocumentResponse] = []
        for hit in hits:
            payload = hit.payload or {}
            try:
                results.append(DocumentResponse(**payload))
            except Exception as parse_err:
                logger.debug(
                    "Skipping malformed vector payload for %s: %s",
                    payload.get("id"),
                    parse_err,
                )
        return results

    def _merge_results(
        self,
        vector_results: List[DocumentResponse],
        es_results: List[DocumentResponse],
        limit: int,
    ) -> List[DocumentResponse]:
        merged: List[DocumentResponse] = []
        seen: set[str] = set()

        for doc in vector_results:
            if doc.id in seen:
                continue
            merged.append(doc)
            seen.add(doc.id)

        for doc in es_results:
            if doc.id in seen:
                continue
            merged.append(doc)
            seen.add(doc.id)

        return merged[:limit]

    async def search_documents(self, search_query: SearchQuery) -> SearchResponse:
        es_task = asyncio.create_task(self._search_elasticsearch(search_query))
        vector_task = (
            asyncio.create_task(self._search_vector(search_query))
            if self.vector_service
            else None
        )

        es_total, es_results, es_took = await es_task
        vector_results = await vector_task if vector_task else []

        merged_results = self._merge_results(
            vector_results=vector_results,
            es_results=es_results,
            limit=search_query.size,
        )
        total = max(es_total, len(vector_results), len(merged_results))

        return SearchResponse(total=total, results=merged_results, took=es_took)

    async def get_all_documents(self, size: int = 100) -> List[DocumentResponse]:
        try:
            response = await self.client.search(
                index=self.index_name,
                body={
                    "query": {"match_all": {}},
                    "size": size,
                    "sort": [{"created_at": {"order": "desc"}}],
                },
            )
            hits = response["hits"]["hits"]
            results = [DocumentResponse(**hit["_source"]) for hit in hits]

            return results
        except (NotFoundError, ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Failed to get all documents: {e}")


document_service = DocumentService()
