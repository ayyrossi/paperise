"""
ASCII art transformation - renders image as colored ASCII characters.
"""

import click
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext, CTX_VERBOSE
from utils.io_utils import hex_to_bgr, resolve_color, validate_color_param


@TransformationRegistry.register('ascii')
class AsciiTransformation(BaseTransformation):
    """
    Render image as ASCII art with colored characters.
    Each pixel in the input image is replaced with an ASCII character
    colored to match the pixel's color. Works best with pixelated/downsampled images.

    Parameters:
        chars (str): Characters to use for ASCII art, darkest to brightest
                     (default: " .:-=+*#%@")
        font (str): Font name or path to TTF file (default: "monospace")
        font_size (int): Font size in points (default: 12)
        background: Background color - either:
                    - Hex color string (e.g., "#000000")
                    - Integer (1-indexed) referencing quantize palette color
                    (default: "#000000")
        char_aspect_ratio (float): Character width/height ratio for spacing
                                   (default: 0.6, typical for monospace fonts)
        font_fallback_paths (list): List of font paths to try if named font not found
    """

    def validate_params(self) -> None:
        """Validate ASCII parameters."""
        chars = self.params.get('chars', " .:-=+*#%@")
        if not isinstance(chars, str) or len(chars) < 2:
            raise ValueError("chars must be a string with at least 2 characters")

        font = self.params.get('font', 'monospace')
        if not isinstance(font, str):
            raise ValueError("font must be a string")

        font_size = self.params.get('font_size', 12)
        if not isinstance(font_size, int) or font_size < 1:
            raise ValueError("font_size must be a positive integer")

        char_aspect_ratio = self.params.get('char_aspect_ratio', 0.6)
        if not isinstance(char_aspect_ratio, (int, float)) or char_aspect_ratio <= 0:
            raise ValueError("char_aspect_ratio must be a positive number")

        validate_color_param(self.params.get('background', '#000000'), 'background')

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Convert image to colored ASCII art.

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Image with ASCII art rendered
        """
        chars = self.params.get('chars', " .:-=+*#%@")
        font_name = self.params.get('font', 'monospace')
        font_size = self.params.get('font_size', 12)
        char_aspect_ratio = self.params.get('char_aspect_ratio', 0.6)
        background_param = self.params.get('background', '#000000')
        verbose = context.metadata.get(CTX_VERBOSE, False)

        bg_color_bgr = resolve_color(background_param, context.palette, 'ascii')

        # Convert BGR to RGB for PIL
        bg_color_rgb = (bg_color_bgr[2], bg_color_bgr[1], bg_color_bgr[0])

        # Load font
        font = self._load_font(font_name, font_size, verbose)

        # Get character dimensions
        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), 'M', font=font)
        char_width = bbox[2] - bbox[0]
        char_height = bbox[3] - bbox[1]

        # Get input image dimensions
        input_height, input_width = image.shape[:2]

        # Calculate output image dimensions
        output_width = int(input_width * char_width)
        output_height = int(input_height * char_height)

        # Create output image
        output = Image.new('RGB', (output_width, output_height), bg_color_rgb)
        draw = ImageDraw.Draw(output)

        # Convert to grayscale for brightness calculation
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Process each pixel
        for y in range(input_height):
            for x in range(input_width):
                # Get brightness value
                brightness = gray[y, x]

                # Map brightness to character
                char_idx = int(brightness / 255 * (len(chars) - 1))
                char = chars[char_idx]

                # Get color for this pixel (BGR format)
                if len(image.shape) == 3:
                    pixel_bgr = image[y, x]
                    # Convert BGR to RGB for PIL
                    if len(pixel_bgr) == 3:
                        pixel_rgb = (int(pixel_bgr[2]), int(pixel_bgr[1]), int(pixel_bgr[0]))
                    else:
                        # Handle BGRA
                        pixel_rgb = (int(pixel_bgr[2]), int(pixel_bgr[1]), int(pixel_bgr[0]))
                else:
                    # Grayscale image
                    pixel_rgb = (brightness, brightness, brightness)

                # Calculate character position
                char_x = int(x * char_width)
                char_y = int(y * char_height)

                # Draw character
                draw.text((char_x, char_y), char, fill=pixel_rgb, font=font)

        # Convert PIL image back to OpenCV format (BGR)
        output_array = np.array(output)
        output_bgr = cv2.cvtColor(output_array, cv2.COLOR_RGB2BGR)

        return output_bgr

    def _load_font(self, font_name: str, font_size: int, verbose: bool = False) -> ImageFont.FreeTypeFont:
        """
        Load a font for text rendering.

        Args:
            font_name: Font name or path to TTF file
            font_size: Font size in points
            verbose: Whether to print diagnostic messages

        Returns:
            PIL ImageFont object
        """
        import subprocess

        try:
            # Try as path first
            if Path(font_name).exists():
                return ImageFont.truetype(font_name, font_size)

            # Try to resolve font name using fc-match (Linux/Unix)
            try:
                result = subprocess.run(
                    ['fc-match', '-f', '%{file}', font_name],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout:
                    font_path = result.stdout.strip()
                    if Path(font_path).exists():
                        if verbose:
                            click.echo(f"  → Using font: {font_path}")
                        return ImageFont.truetype(font_path, font_size)
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

            # Fall back to configured font paths
            if verbose:
                click.echo(f"  → Font '{font_name}' not found, using fallback")
            font_paths = self.params.get('font_fallback_paths', [])
            for path in font_paths:
                if Path(path).exists():
                    if verbose:
                        click.echo(f"  → Using fallback font: {path}")
                    return ImageFont.truetype(path, font_size)

            # Last resort: use PIL default (will be very small)
            if verbose:
                click.echo("  → WARNING: No suitable font found, using PIL default (may appear very small)")
            return ImageFont.load_default()
        except Exception as e:
            if verbose:
                click.echo(f"  → WARNING: Error loading font: {e}, using PIL default")
            return ImageFont.load_default()
