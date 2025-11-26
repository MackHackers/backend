import uuid
import json
from datetime import datetime
from typing import Optional
from schemas.documents import DocumentBase

from db.immudb_client import immudb

DOC_PREFIX = b"doc:"
DOC_INDEX = b"docs:index"


def _load_index() -> list:
    entry = immudb.get(DOC_INDEX)
    print(DOC_INDEX, entry)
    if not entry:
        print("No index found, returning empty list")
        return []
    try:
        print("Loading index from immudb")
        return json.loads(entry.value.decode())
    except:
        print("Failed to load index, returning empty list")
        return []


def _save_index(index: list):
    immudb.set(DOC_INDEX, json.dumps(index).encode())


def create_document(data: dict, creator: str) -> dict:
    now = datetime.utcnow().isoformat() + "Z"

    doc = {
        "id": data["id"],
        "deleted": False,
        "title": data["title"],
        "content": data["content"],
        "author": data.get("author"),
        "tags": data.get("tags", []),
        "metadata": data.get("metadata", {}),
        "creator": creator,
        "created_at": now,
        "updated_at": now,
    }

    # save document in immudb
    immudb.set(DOC_PREFIX + data["id"].encode(), json.dumps(doc).encode())

    # update index
    idx = _load_index()
    idx.append(data["id"])
    _save_index(idx)

    return doc

def delete_document(doc_id: str):
    entry = immudb.get(DOC_PREFIX + doc_id.encode())
    if not entry:
        return None

    data = json.loads(entry.value.decode())

    data["deleted"] = not bool(data["deleted"])
    immudb.set(DOC_PREFIX + data["id"].encode(), json.dumps(data).encode())

    return data


def update_document(data: DocumentBase):
    entry = immudb.get(DOC_PREFIX + data.id.encode())
    print(entry)

    if not entry:
        return None
    
    entry = json.loads(entry.value.decode())
    now = datetime.utcnow().isoformat() + "Z"

    new_doc = {
        "id": entry["id"],
        "deleted": False,
        "title": data.title,
        "content": data.content,
        "author": data.author,
        "tags": data.tags,
        "metadata": data.metadata,
        "creator": entry.get("creator"),
        "created_at": entry.get("created_at"),
        "updated_at": now,
    }

    # save document in immudb
    immudb.set(DOC_PREFIX + entry["id"].encode(), json.dumps(new_doc).encode())


    return new_doc


def get_document(doc_id: str) -> Optional[dict]:
    entry = immudb.get(DOC_PREFIX + doc_id.encode())
    if not entry:
        return None
    return json.loads(entry.value.decode())


def list_documents() -> list[str]:
    return _load_index()
