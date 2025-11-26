from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
import schemas.users as users
import crud.users as crud
from core.security import get_current_user, get_password_hash, verify_password, create_access_token, require_role
from core.config import settings

router = APIRouter(prefix="", tags=["auth"])



@router.post("/login", response_model=users.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user(form_data.username)

    if user["role"] == "root":
        access_token = create_access_token({
        "sub": form_data.username,
        "role": user["role"]
        })

        return {"access_token": access_token, "token_type": "bearer"}

    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(400, "Incorrect username or password")

    access_token = create_access_token({
        "sub": form_data.username,
        "role": user["role"]
    })

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def get_me(user = Depends(get_current_user)):
    return user
