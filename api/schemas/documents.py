from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class DocumentBase(BaseModel):
    id: str
    deleted: bool
    title: str 
    content: str 
    author: str
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime 
    updated_at: datetime



class DocumentOut(DocumentBase):
    id: str
    creator: str
    created_at: str
    updated_at: str


class DocumentUpdate(BaseModel):
    title: Optional[str]
    content: Optional[str] 
    author: Optional[str] 
    tags: Optional[List[str]] 
    metadata: Optional[Dict[str, Any]] 


class DocumentResponse(BaseModel):
    id: str
    title: str
    content: str
    author: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SearchQuery(BaseModel):
    query: str
    size: int
    from_: int 


class SearchResponse(BaseModel):
    total: int
    results: List[DocumentResponse]
    took: int
