"""User API routes."""

from api.services import get_user_service
from common.models.user import User
from common.services.user_service import UserService
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["users"], redirect_slashes=False)


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def add_user(user: User, service: UserService = Depends(get_user_service)) -> User:
    if not service.add_user(user):
        raise HTTPException(status_code=400, detail="User with this ID already exists.")
    return user


@router.get("", response_model=list[User])
@router.get("/", response_model=list[User])
async def list_users(service: UserService = Depends(get_user_service)) -> list[User]:
    return service.list_users()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, service: UserService = Depends(get_user_service)):
    if not service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    return None
