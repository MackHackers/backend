import uuid
import json
from datetime import datetime
from typing import Optional

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


def get_document(doc_id: str) -> Optional[dict]:
    entry = immudb.get(DOC_PREFIX + doc_id.encode())
    if not entry:
        return None
    return json.loads(entry.value.decode())


def list_documents() -> list:
    return _load_index()
