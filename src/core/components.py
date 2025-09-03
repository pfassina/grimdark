"""Component-based entity system for game objects.

This module provides the foundation for a classical game component system where
entities are composed of discrete, focused components that handle specific aspects
of game functionality.
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    pass


class Component(ABC):
    """Base class for all components in the system.
    
    Components represent specific aspects of game entity functionality
    (health, movement, combat, etc.) and contain both data and methods
    related to that functionality.
    """
    
    def __init__(self, entity: "Entity"):
        """Initialize component with reference to owning entity.
        
        Args:
            entity: The entity this component belongs to
        """
        self.entity = entity
    
    @abstractmethod
    def get_component_name(self) -> str:
        """Get the name identifier for this component type."""
        pass


class Entity:
    """Container for components that together define a game object.
    
    An entity is essentially a unique ID plus a collection of components
    that define its behavior and properties. The entity provides access
    to components and manages component lifecycle.
    """
    
    def __init__(self):
        """Initialize entity with unique ID and empty component collection."""
        self.entity_id: str = str(uuid.uuid4())
        self.components: dict[str, Component] = {}
    
    def add_component(self, component: Component) -> None:
        """Add a component to this entity.
        
        Args:
            component: The component to add
            
        Raises:
            ValueError: If a component of this type already exists
        """
        component_name = component.get_component_name()
        if component_name in self.components:
            raise ValueError(f"Entity already has component: {component_name}")
        
        self.components[component_name] = component
    
    def get_component(self, component_name: str) -> Optional[Component]:
        """Get a component by name.
        
        Args:
            component_name: Name of the component to retrieve
            
        Returns:
            The component if it exists, None otherwise
        """
        return self.components.get(component_name)
    
    def require_component(self, component_name: str) -> Component:
        """Get a component by name, raising an error if it doesn't exist.
        
        Args:
            component_name: Name of the component to retrieve
            
        Returns:
            The component
            
        Raises:
            ValueError: If the component doesn't exist
        """
        component = self.components.get(component_name)
        if component is None:
            raise ValueError(f"Entity missing required component: {component_name}")
        return component
    
    def has_component(self, component_name: str) -> bool:
        """Check if this entity has a specific component.
        
        Args:
            component_name: Name of the component to check for
            
        Returns:
            True if the component exists, False otherwise
        """
        return component_name in self.components
    
    def remove_component(self, component_name: str) -> Optional[Component]:
        """Remove a component from this entity.
        
        Args:
            component_name: Name of the component to remove
            
        Returns:
            The removed component if it existed, None otherwise
        """
        return self.components.pop(component_name, None)
    
    def get_all_components(self) -> dict[str, Component]:
        """Get all components on this entity.
        
        Returns:
            Dictionary of component_name -> component
        """
        return self.components.copy()


class ComponentError(Exception):
    """Base exception for component system errors."""
    pass


class MissingComponentError(ComponentError):
    """Raised when trying to access a component that doesn't exist."""
    
    def __init__(self, entity_id: str, component_name: str):
        super().__init__(f"Entity {entity_id} missing component: {component_name}")
        self.entity_id = entity_id
        self.component_name = component_name


class DuplicateComponentError(ComponentError):
    """Raised when trying to add a component that already exists."""
    
    def __init__(self, entity_id: str, component_name: str):
        super().__init__(f"Entity {entity_id} already has component: {component_name}")
        self.entity_id = entity_id
        self.component_name = component_name