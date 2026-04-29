"""
Image I/O utilities for loading, saving, and auxiliary outputs.
"""

import cv2
import numpy as np
from pathlib import Path


def load_image(image_path: str) -> np.ndarray:
    """
    Load an image from file.

    Args:
        image_path: Path to input image

    Returns:
        Image as numpy array in BGR format

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be loaded
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    return image



def hex_to_bgr(hex_color: str) -> tuple:
    """
    Convert hex color string to BGR tuple.

    Args:
        hex_color: Hex color string (e.g., "#FF5733" or "FF5733")

    Returns:
        BGR color tuple

    Raises:
        ValueError: If hex color is invalid
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')

    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b, g, r)  # OpenCV uses BGR
    except ValueError:
        raise ValueError(f"Invalid hex color: {hex_color}")


def validate_color_param(value, param_name: str = "color") -> None:
    """Validate that a color param is a valid hex string or positive int (palette index)."""
    if isinstance(value, int):
        if value < 1:
            raise ValueError(f"{param_name}: palette index must be >= 1 (1-indexed)")
    elif isinstance(value, str):
        try:
            hex_to_bgr(value)
        except ValueError:
            raise ValueError(f"{param_name}: invalid hex color '{value}'")
    else:
        raise ValueError(f"{param_name} must be a hex string or int (palette index)")


def resolve_color(color_param, palette: list, context_name: str = "transformation") -> tuple:
    """Resolve hex string or 1-indexed palette reference to a BGR tuple."""
    if isinstance(color_param, int):
        if not palette:
            raise ValueError(
                f"Cannot use palette color index: no palette available. "
                f"Ensure a quantize or palette transformation runs before {context_name}."
            )
        palette_idx = color_param - 1
        if palette_idx < 0 or palette_idx >= len(palette):
            raise ValueError(
                f"Palette color index {color_param} out of range. "
                f"Palette has {len(palette)} colors (valid: 1-{len(palette)})"
            )
        return tuple(palette[palette_idx])
    else:
        return hex_to_bgr(color_param)
