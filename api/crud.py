import json
from db.immudb_client import immudb
from core.config import settings

USER_PREFIX = b"user:"

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

