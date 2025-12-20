"""User API routes."""

from typing import list
from fastapi import APIRouter, HTTPException, status, Depends
from api.models.user import User
from api.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

# Dependency for user service (singleton for in-memory demo)
user_service = UserService()

def get_user_service() -> UserService:
    return user_service

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def add_user(user: User, service: UserService = Depends(get_user_service)) -> User:
    if not service.add_user(user):
        raise HTTPException(status_code=400, detail="User with this ID already exists.")
    return user

@router.get("/", response_model=list[User])
async def list_users(service: UserService = Depends(get_user_service)) -> list[User]:
    return service.list_users()

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, service: UserService = Depends(get_user_service)):
    if not service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    return None
