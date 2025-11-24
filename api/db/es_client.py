import logging
from elasticsearch import Elasticsearch, AsyncElasticsearch

from .config import settings

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    def __init__(self):
        self._client = None
        self._async_client = None

    def get_client(self) -> Elasticsearch:
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def get_async_client(self) -> AsyncElasticsearch:
        if self._async_client is None:
            self._async_client = self._create_async_client()
        return self._async_client

    def _build_config(self) -> dict:
        config = {
            "hosts": [
                f"{settings.elasticsearch_scheme}://{settings.elasticsearch_host}:{settings.elasticsearch_port}"
            ]
        }

        if settings.elasticsearch_username and settings.elasticsearch_password:
            config["basic_auth"] = (
                settings.elasticsearch_username,
                settings.elasticsearch_password,
            )

        if settings.elasticsearch_ca_certs:
            config["ca_certs"] = settings.elasticsearch_ca_certs

        return config

    def _create_client(self) -> Elasticsearch:
        logger.info("Creating synchronous Elasticsearch client")
        return Elasticsearch(**self._build_config())

    def _create_async_client(self) -> AsyncElasticsearch:
        logger.info("Creating asynchronous Elasticsearch client")
        return AsyncElasticsearch(**self._build_config())

    async def close(self):
        if self._client:
            self._client.close()
        if self._async_client:
            await self._async_client.close()
        logger.info("Elasticsearch connections closed")


es_client = ElasticsearchClient()
