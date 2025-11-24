import datetime
import json
import uuid
from db.immudb_client import immudb
from core.config import settings

USER_PREFIX = b"user:"
DOC_PREFIX = b"doc:"
DOC_INDEX_KEY = b"docs:index"

def save_user(username: str, hashed_password: str, role: str):
    key = USER_PREFIX + username.encode()
    value = json.dumps({
        "password": hashed_password,
        "role": role
    }).encode()
    immudb.set(key, value)


def get_user(username: str):
    if username == settings.root_username:
        return {
            "password": settings.root_password,
            "role": "root"
        }

    key = USER_PREFIX + username.encode()
    entry = immudb.get(key)

    if not entry:
        return None
    
    return json.loads(entry.value.decode())


def _get_index_list() -> list:
    entry = immudb.get(DOC_INDEX_KEY)
    if not entry:
        return []
    try:
        return json.loads(entry.value.decode())
    except Exception:
        return []


def _save_index_list(idx: list) -> None:
    immudb.set(DOC_INDEX_KEY, json.dumps(idx).encode())


def save_document(header: str, body: str, metadata: dict, creator: str) -> dict:
    """
    Create a new document, store it, and add to index.
    Returns the saved document dict (with id, created_at, etc).
    """
    doc_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    doc = {
        "id": doc_id,
        "header": header,
        "body": body,
        "metadata": metadata or {},
        "creator": creator,
        "created_at": created_at
    }
    key = DOC_PREFIX + doc_id.encode()
    immudb.set(key, json.dumps(doc).encode())

    # update index (note: simple approach — may race under heavy concurrency)
    idx = _get_index_list()
    idx.append(doc_id)
    _save_index_list(idx)

    return doc