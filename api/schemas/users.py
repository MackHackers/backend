from typing import Literal
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    password: str
    role: Literal["viewer", "manager", "root"] = "viewer"

