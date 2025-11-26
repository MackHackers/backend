from fastapi import APIRouter, HTTPException, Depends
import schemas.users as users
import crud.users as crud
from core.security import get_current_user, get_password_hash, verify_password, create_access_token, require_role
from core.config import settings

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register")
async def register(payload: users.UserCreate, user = Depends(get_current_user), allowed = Depends(require_role("manager"))):
    if crud.get_user(payload.username):
        raise HTTPException(400, "User already exists")
    
    if payload.username == settings.root_username:
        raise HTTPException(400, "Cannot create the root user")

    hashed = get_password_hash(payload.password)
    crud.save_user(payload.username, hashed, payload.role)

    return {"username": payload.username, "role": payload.role}

@router.get("/")
async def get_all_usernames(user = Depends(get_current_user), allowed = Depends(require_role("manager"))):
    return crud.list_users() or []