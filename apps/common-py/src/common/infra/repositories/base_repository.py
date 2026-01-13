"""Abstract base repository for data access."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base class for all repositories.
    
    Type parameter T represents the domain model type (e.g., User, Document, Agent).
    
    Responsibilities:
    - Define common repository interface
    - Ensure consistent return types (domain models, not dicts)
    - Provide type safety for repository implementations
    """

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity.
        
        Args:
            entity: Domain model instance to create
            
        Returns:
            Created domain model instance
            
        Raises:
            Exception: If entity already exists or creation fails
        """
        pass

    @abstractmethod
    def get_by_id(self, entity_id: str) -> T | None:
        """Get entity by ID.
        
        Args:
            entity_id: Entity ID to retrieve
            
        Returns:
            Domain model instance or None if not found
        """
        pass

    @abstractmethod
    def list_all(self, offset: int = 0, limit: int = 10) -> tuple[list[T], int]:
        """List all entities with pagination.
        
        Args:
            offset: Number of items to skip
            limit: Maximum number of items to return
            
        Returns:
            Tuple of (list of domain models, total count)
        """
        pass

    @abstractmethod
    def update(self, entity_id: str, entity: T) -> T | None:
        """Update an existing entity.
        
        Args:
            entity_id: Entity ID to update
            entity: Updated domain model instance
            
        Returns:
            Updated domain model instance or None if not found
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: Entity ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
