"""
Image I/O utilities for loading, saving, and auxiliary outputs.
"""

import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Optional


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


def save_image(image: np.ndarray, output_path: str) -> None:
    """
    Save an image to file.

    Args:
        image: Image as numpy array
        output_path: Path to save image

    Raises:
        ValueError: If image cannot be saved
    """
    success = cv2.imwrite(output_path, image)
    if not success:
        raise ValueError(f"Could not save image to: {output_path}")


def save_palette(palette: list, output_path: str) -> None:
    """
    Save color palette as hex colors to text file.

    Args:
        palette: List of BGR color tuples
        output_path: Path to save palette file
    """
    with open(output_path, 'w') as f:
        for color in palette:
            # Convert BGR to RGB for hex representation
            if len(color) == 3:
                b, g, r = color
            else:
                # Handle BGRA
                b, g, r = color[:3]
            hex_color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            f.write(hex_color + "\n")


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


def generate_ascii_image(
    ascii_text: str,
    output_path: str,
    font_name: str = "monospace",
    font_size: int = 10,
    bg_color: tuple = (0, 0, 0),
    fg_color: tuple = (255, 255, 255)
) -> None:
    """
    Render ASCII text to an image file.

    Args:
        ascii_text: ASCII art string (with newlines)
        output_path: Path to save ASCII image
        font_name: Font name or path to TTF file
        font_size: Font size in points
        bg_color: Background color (RGB)
        fg_color: Foreground color (RGB)
    """
    # Split text into lines
    lines = ascii_text.split('\n')
    if not lines:
        return

    # Try to load font
    try:
        # Try as path first
        if Path(font_name).exists():
            font = ImageFont.truetype(font_name, font_size)
        else:
            # Try common monospace fonts
            font_paths = [
                f"/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                f"/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
                f"/System/Library/Fonts/Courier.dfont",
                f"C:\\Windows\\Fonts\\consola.ttf",
            ]
            font = None
            for path in font_paths:
                if Path(path).exists():
                    font = ImageFont.truetype(path, font_size)
                    break
            if font is None:
                font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Calculate image size
    # Use a temporary draw to measure text
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    # Get dimensions of a single character
    bbox = temp_draw.textbbox((0, 0), 'M', font=font)
    char_width = bbox[2] - bbox[0]
    char_height = bbox[3] - bbox[1]

    # Calculate image dimensions
    max_line_length = max(len(line) for line in lines) if lines else 0
    width = max_line_length * char_width + 20  # Add padding
    height = len(lines) * char_height + 20

    # Create image
    image = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # Draw text
    y = 10
    for line in lines:
        draw.text((10, y), line, fill=fg_color, font=font)
        y += char_height

    # Save image
    image.save(output_path)


def image_to_ascii(
    image: np.ndarray,
    chars: str = " .:-=+*#%@",
    width: Optional[int] = None
) -> str:
    """
    Convert image to ASCII art string.

    Args:
        image: Input image (BGR or grayscale)
        chars: Characters to use for ASCII art (darkest to brightest)
        width: Target width in characters (maintains aspect ratio)

    Returns:
        ASCII art string
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Resize if width specified
    if width is not None:
        aspect_ratio = gray.shape[0] / gray.shape[1]
        height = int(width * aspect_ratio * 0.55)  # Adjust for character aspect ratio
        gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)

    # Convert to ASCII
    ascii_chars = []
    for row in gray:
        line = ""
        for pixel in row:
            # Map pixel value (0-255) to character index
            char_idx = int(pixel / 255 * (len(chars) - 1))
            line += chars[char_idx]
        ascii_chars.append(line)

    return '\n'.join(ascii_chars)
