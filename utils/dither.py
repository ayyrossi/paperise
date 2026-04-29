"""
Dithering transformation.
"""

import cv2
import numpy as np
from pathlib import Path
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext


@TransformationRegistry.register('dither')
class DitherTransformation(BaseTransformation):
    """
    Apply dithering to image.

    Parameters:
        dither_type (str): Type of dithering - 'floyd_steinberg', 'ordered', or 'bayer'
        amount (float): Dithering strength (0.0 to 1.0, default: 1.0)
    """

    # Bayer matrix for ordered dithering
    BAYER_MATRIX_8x8 = np.array([
        [ 0, 48, 12, 60,  3, 51, 15, 63],
        [32, 16, 44, 28, 35, 19, 47, 31],
        [ 8, 56,  4, 52, 11, 59,  7, 55],
        [40, 24, 36, 20, 43, 27, 39, 23],
        [ 2, 50, 14, 62,  1, 49, 13, 61],
        [34, 18, 46, 30, 33, 17, 45, 29],
        [10, 58,  6, 54,  9, 57,  5, 53],
        [42, 26, 38, 22, 41, 25, 37, 21]
    ], dtype=np.float32) / 64.0 - 0.5

    def validate_params(self) -> None:
        """Validate dithering parameters."""
        dither_type = self.params.get('dither_type', 'floyd_steinberg')
        amount = self.params.get('amount', 1.0)

        valid_types = ['floyd_steinberg', 'ordered', 'bayer']
        if dither_type not in valid_types:
            raise ValueError(
                f"dither_type must be one of {valid_types}, got: {dither_type}"
            )

        if not isinstance(amount, (int, float)):
            raise ValueError("amount must be a number")

        if amount < 0 or amount > 1:
            raise ValueError("amount must be between 0 and 1")

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Apply dithering to image.

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Dithered image
        """
        dither_type = self.params.get('dither_type', 'floyd_steinberg')
        amount = self.params.get('amount', 1.0)

        # Handle alpha channel
        has_alpha = len(image.shape) == 3 and image.shape[2] == 4
        if has_alpha:
            alpha_channel = image[:, :, 3]
            image_rgb = image[:, :, :3]
        else:
            image_rgb = image

        # Apply dithering based on type
        if dither_type == 'floyd_steinberg':
            dithered = self._floyd_steinberg_dither(image_rgb, amount)
        elif dither_type in ['ordered', 'bayer']:
            dithered = self._bayer_dither(image_rgb, amount)
        else:
            dithered = image_rgb

        # Restore alpha channel
        if has_alpha:
            dithered = np.dstack([dithered, alpha_channel])

        return dithered

    def _floyd_steinberg_dither(self, image: np.ndarray, amount: float) -> np.ndarray:
        """
        Apply Floyd-Steinberg error diffusion dithering.

        Error diffusion pattern:
                X   7/16
            3/16 5/16 1/16

        Args:
            image: Input image (BGR format)
            amount: Dithering strength (0.0 to 1.0)

        Returns:
            Dithered image
        """
        # Work on a copy with float precision
        img = image.astype(np.float32)
        height, width, channels = img.shape

        for y in range(height):
            for x in range(width):
                old_pixel = img[y, x].copy()

                # Quantize to nearest color (0 or 255)
                new_pixel = np.round(old_pixel / 255.0) * 255.0

                # Calculate error
                error = (old_pixel - new_pixel) * amount

                # Set new pixel value
                img[y, x] = new_pixel

                # Distribute error to neighboring pixels
                if x + 1 < width:
                    img[y, x + 1] += error * 7/16

                if y + 1 < height:
                    if x > 0:
                        img[y + 1, x - 1] += error * 3/16
                    img[y + 1, x] += error * 5/16
                    if x + 1 < width:
                        img[y + 1, x + 1] += error * 1/16

        # Clip values to valid range
        img = np.clip(img, 0, 255)
        return img.astype(np.uint8)

    def _bayer_dither(self, image: np.ndarray, amount: float) -> np.ndarray:
        """
        Apply Bayer ordered dithering using 8x8 matrix.

        Args:
            image: Input image (BGR format)
            amount: Dithering strength (0.0 to 1.0)

        Returns:
            Dithered image
        """
        height, width, channels = image.shape

        # Create tiled Bayer matrix to match image size
        tile_y = (height // 8) + 1
        tile_x = (width // 8) + 1
        bayer_tiled = np.tile(self.BAYER_MATRIX_8x8, (tile_y, tile_x))
        bayer_tiled = bayer_tiled[:height, :width]

        # Expand to match channels
        bayer_tiled = np.expand_dims(bayer_tiled, axis=2)
        bayer_tiled = np.repeat(bayer_tiled, channels, axis=2)

        # Normalize image to 0-1 range
        img = image.astype(np.float32) / 255.0

        # Apply dithering threshold
        threshold = bayer_tiled * amount
        dithered = (img + threshold > 0.5).astype(np.float32)

        # Convert back to 0-255 range
        dithered = (dithered * 255).astype(np.uint8)

        return dithered
