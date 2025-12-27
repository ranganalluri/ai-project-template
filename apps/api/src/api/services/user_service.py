"""In-memory user service for User API."""

from typing import ClassVar

from common.models.user import User


class UserService:
    """Service for managing users in memory."""

    users: ClassVar[dict[str, User]] = {}

    def add_user(self, user: User) -> bool:
        if user.user_id in UserService.users:
            return False
        UserService.users[user.user_id] = user
        return True

    def get_user(self, user_id: str) -> User | None:
        return UserService.users.get(user_id)

    def list_users(self) -> list[User]:
        return list(UserService.users.values())

    def delete_user(self, user_id: str) -> bool:
        if user_id in UserService.users:
            del UserService.users[user_id]
            return True
        return False
