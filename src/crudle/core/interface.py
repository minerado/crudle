from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union


class AdapterInterface(ABC):
    """Interface that all adapters must implement.

    This interface defines the contract that all adapters must follow,
    ensuring consistency across different database backends.
    """

    @abstractmethod
    def insert(self, model: Type, **kwargs) -> Any:
        """Insert a new record.

        Args:
            model: The model class to insert
            **kwargs: Attributes for the new record

        Returns:
            The created model instance or document data
        """
        pass

    @abstractmethod
    def get(self, model: Type, id: Union[str, int]) -> Optional[Any]:
        """Get a record by ID.

        Args:
            model: The model class
            id: The record ID

        Returns:
            The model instance or document data, or None if not found
        """
        pass

    @abstractmethod
    def get_by(self, model: Type, **filters) -> Optional[Any]:
        """Get a record by specified filters.

        Args:
            model: The model class
            **filters: Filter criteria (e.g., age__gte=18, name="John")

        Returns:
            The model instance or document data, or None if not found
        """
        pass

    @abstractmethod
    def list(self, model: Type, **filters) -> List[Any]:
        """List records with optional filters.

        Args:
            model: The model class
            **filters: Filter criteria (e.g., age__gte=18, name="John")

        Returns:
            List of model instances or document data
        """
        pass

    @abstractmethod
    def update(self, model: Type, id: Union[str, int], **kwargs) -> Optional[Any]:
        """Update a record by ID.

        Args:
            model: The model class
            id: The record ID
            **kwargs: Attributes to update

        Returns:
            The updated model instance or document data, or None if not found
        """
        pass

    @abstractmethod
    def update_by(
        self,
        model: Type,
        filters: Dict[str, Any],
        should_raise: bool = False,
        **kwargs,
    ) -> Optional[Any]:
        """Update a record by specified filters.

        Args:
            model: The model class
            filters: Filter criteria to find the record
            should_raise: Whether to raise if no record is found
            **kwargs: Attributes to update

        Returns:
            The updated model instance or document data, or None if not found
        """
        pass

    @abstractmethod
    def upsert_by(self, model: Type, filters: Dict[str, Any], **kwargs) -> Any:
        """Update or insert a record based on filters.

        Args:
            model: The model class
            filters: Filter criteria to find the record
            **kwargs: Attributes for the record

        Returns:
            The updated or created model instance or document data
        """
        pass

    @abstractmethod
    def delete(self, model: Type, id: Union[str, int]) -> Optional[Any]:
        """Delete a record by ID.

        Args:
            model: The model class
            id: The record ID

        Returns:
            The deleted model instance or document data, or None if not found
        """
        pass

    @abstractmethod
    def delete_by(self, model: Type, **filters) -> Optional[Any]:
        """Delete a record by specified filters.

        Args:
            model: The model class
            **filters: Filter criteria to find the record

        Returns:
            The deleted model instance or document data, or None if not found
        """
        pass

    @abstractmethod
    def count(self, model: Type, field: Optional[str] = None, **filters) -> int:
        """Count records matching filters.

        Args:
            model: The model class
            field: Optional field for API parity across adapters
            **filters: Filter criteria

        Returns:
            Number of records matching the filters
        """
        pass
