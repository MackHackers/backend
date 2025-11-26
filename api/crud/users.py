import json
from db.immudb_client import immudb
from core.config import settings

USER_PREFIX = b"user:"
USER_INDEX = b"user:index"


def _load_index() -> list:
    entry = immudb.get(USER_INDEX)
    print(USER_INDEX, entry)
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
    immudb.set(USER_INDEX, json.dumps(index).encode())

def save_user(username: str, hashed_password: str, role: str):
    key = USER_PREFIX + username.encode()
    value = json.dumps({
        "password": hashed_password,
        "role": role
    }).encode()
    
    immudb.set(key, value)

    idx = _load_index()
    idx.append(username)
    _save_index(idx)

def list_users() -> list[str]:
    return _load_index()


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
