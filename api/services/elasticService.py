import logging
from pydoc import doc
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from elasticsearch.exceptions import (
    NotFoundError,
    ConnectionError,
    RequestError,
    ApiError,
)
from elasticsearch.helpers import async_bulk

from schemas.documents import (
    DocumentBase,
    DocumentResponse,
    DocumentUpdate,
    SearchQuery,
    SearchResponse,
)
from db.es_client import es_client
from core.config import settings



class DocumentService:
    def __init__(self):
        self.index_name = settings.documents_index
        self.client = es_client.get_async_client()

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
            return current_doc
        except (NotFoundError, ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Failed to update document: {e}")

    async def delete_document(self, document_id: UUID) -> bool:
        try:
            response = await self.client.delete(
                index=self.index_name, id=str(document_id)
            )
            deleted = response["result"] == "deleted"
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

    async def search_documents(self, search_query: SearchQuery) -> SearchResponse:
        default_fields = ["title^3", "content^2", "author^2", "tags^2"]
        query_body = {
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

        try:
            response = await self.client.search(index=self.index_name, body=query_body)
            hits = response["hits"]["hits"]
            results = [DocumentResponse(**hit["_source"]) for hit in hits]

            return SearchResponse(
                total=response["hits"]["total"]["value"],
                results=results,
                took=response["took"],
            )
        except (NotFoundError, ConnectionError, RequestError, ApiError) as e:
            raise Exception(f"Search failed: {e}")

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
