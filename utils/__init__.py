"""
Utils package - Auto-imports all transformation modules to trigger registration.
"""

# Import all transformation modules to register them with TransformationRegistry
from utils.pixelate import PixelateTransformation
from utils.quantize import QuantizeTransformation
from utils.palette import PaletteTransformation
from utils.dither import DitherTransformation
from utils.filters import FilterTransformation
from utils.border import BorderTransformation
from utils.resize import ResizeTransformation
from utils.ascii import AsciiTransformation

# Export commonly used classes
from utils.base import (
    BaseTransformation,
    TransformationRegistry,
    TransformationContext
)

__all__ = [
    'BaseTransformation',
    'TransformationRegistry',
    'TransformationContext',
    'PixelateTransformation',
    'QuantizeTransformation',
    'PaletteTransformation',
    'DitherTransformation',
    'FilterTransformation',
    'BorderTransformation',
    'ResizeTransformation',
    'AsciiTransformation',
]
