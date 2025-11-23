from fastapi import APIRouter, Depends
from core.security import get_current_user, require_role


router = APIRouter(prefix="", tags=["protected"])



@router.get("/dashboard")
async def manager_dashboard(
    user = Depends(get_current_user),
    allowed = Depends(require_role("manager"))
):
    return {"msg": f"Welcome manager: {user["username"]}"}