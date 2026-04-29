"""
Base classes and registry pattern for transformation pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Type
import numpy as np

# Context metadata key constants
CTX_ORIGINAL_WIDTH = "original_width"
CTX_ORIGINAL_HEIGHT = "original_height"
CTX_VERBOSE = "verbose"


@dataclass
class TransformationContext:
    """
    Shared context passed through the transformation pipeline.
    Used for storing auxiliary outputs like palettes and metadata.
    """
    palette: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTransformation(ABC):
    """
    Abstract base class for all transformations.
    Each transformation must implement the apply method.
    """

    def __init__(self, params: Dict[str, Any]):
        """
        Initialize transformation with parameters from config.

        Args:
            params: Dictionary of transformation-specific parameters
        """
        self.params = params

    @abstractmethod
    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Apply transformation to image.

        Args:
            image: Input image as numpy array (BGR format from OpenCV)
            context: Shared context for auxiliary outputs

        Returns:
            Transformed image as numpy array
        """
        pass

    def validate_params(self) -> None:
        """
        Optional method to validate transformation parameters.
        Raises ValueError if parameters are invalid.
        """
        pass


class TransformationRegistry:
    """
    Registry for transformation classes using decorator pattern.
    Allows transformations to self-register when modules are imported.
    """

    _registry: Dict[str, Type[BaseTransformation]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a transformation class.

        Usage:
            @TransformationRegistry.register('pixelate')
            class PixelateTransformation(BaseTransformation):
                ...

        Args:
            name: Name to register transformation under (used in config)
        """
        def decorator(transformation_class: Type[BaseTransformation]):
            if name in cls._registry:
                raise ValueError(f"Transformation '{name}' is already registered")
            cls._registry[name] = transformation_class
            return transformation_class
        return decorator

    @classmethod
    def get(cls, name: str) -> Type[BaseTransformation]:
        """
        Get a transformation class by name.

        Args:
            name: Name of the transformation

        Returns:
            Transformation class

        Raises:
            KeyError: If transformation is not registered
        """
        if name not in cls._registry:
            raise KeyError(
                f"Transformation '{name}' not found. "
                f"Available transformations: {', '.join(cls._registry.keys())}"
            )
        return cls._registry[name]

    @classmethod
    def list_transformations(cls) -> list:
        """
        Get list of all registered transformation names.

        Returns:
            List of transformation names
        """
        return list(cls._registry.keys())
