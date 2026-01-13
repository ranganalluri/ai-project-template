"""Mapper utilities for converting between models and DTOs."""

from uuid import uuid4

from common.models.user import User
from common.use_cases.user.queries import UserResponse, UserListResponse
from common.use_cases.user.commands import CreateUserCommand, UpdateUserCommand


class UserMapper:
    """Mapper for User model and DTOs."""

    @staticmethod
    def to_response(user: User) -> UserResponse:
        """Convert User model to UserResponse DTO.

        Args:
            user: User model instance

        Returns:
            UserResponse DTO
        """
        return UserResponse(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
        )

    @staticmethod
    def to_response_list(users: list[User], total: int, page: int, page_size: int) -> UserListResponse:
        """Convert list of User models to UserListResponse DTO.

        Args:
            users: List of User model instances
            total: Total number of users
            page: Current page number
            page_size: Number of users per page

        Returns:
            UserListResponse DTO
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return UserListResponse(
            users=[UserMapper.to_response(user) for user in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def from_create_command(command: CreateUserCommand, user_id: str | None = None) -> User:
        """Convert CreateUserCommand to User model.

        Args:
            command: CreateUserCommand DTO
            user_id: Optional user ID (generates new if not provided)

        Returns:
            User model instance
        """
        return User(
            user_id=user_id or f"user-{uuid4()}",
            name=command.name,
            email=command.email,
        )

    @staticmethod
    def apply_update_command(user: User, command: UpdateUserCommand) -> User:
        """Apply UpdateUserCommand to existing User model.

        Args:
            user: Existing User model instance
            command: UpdateUserCommand DTO

        Returns:
            Updated User model instance
        """
        update_data = command.model_dump(exclude_unset=True)
        return user.model_copy(update=update_data)

    @staticmethod
    def to_cosmos_document(user: User) -> dict:
        """Convert User model to Cosmos DB document format.

        Args:
            user: User model instance

        Returns:
            Dictionary suitable for Cosmos DB storage
        """
        return {
            "id": user.user_id,
            "user_id": user.user_id,
            **user.model_dump(),
        }

    @staticmethod
    def from_cosmos_document(doc: dict) -> User:
        """Convert Cosmos DB document to User model.

        Args:
            doc: Cosmos DB document dictionary

        Returns:
            User model instance
        """
        return User(
            user_id=doc["user_id"],
            name=doc["name"],
            email=doc["email"],
        )
