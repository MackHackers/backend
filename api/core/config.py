from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    immudb_host: str = "localhost"
    immudb_port: int = 3322
    immudb_username: str = "immudb"
    immudb_password: str = "immudb"
    secret_key: str
    access_token_expire_minutes: int = 30
    
    root_username: str = "root"
    root_password: str = "root"


    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_scheme: str = "http"
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    elasticsearch_ca_certs: Optional[str] = None

    documents_index: str = "documents"

    class Config:
        env_file = ".env"


settings = Settings()