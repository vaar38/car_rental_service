from fastapi import APIRouter, Depends

from app.schemas import UserOut
from app.security import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(user=Depends(get_current_user)):
    return user
