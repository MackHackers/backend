from immudb import ImmudbClient
from core.config import settings



class ImmudbWrapper:
    def __init__(self):
        self.client = ImmudbClient(f"{settings.immudb_host}:{settings.immudb_port}")
        self.client.login(settings.immudb_username, settings.immudb_password)


    def set(self, key: bytes, value: bytes):
        return self.client.set(key, value)


    def get(self, key: bytes):
        try:
            return self.client.get(key)
        except Exception:
            return None


immudb = ImmudbWrapper()