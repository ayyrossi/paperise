"""
Pixelate transformation - creates blocky retro pixel aesthetic.
"""

import cv2
import numpy as np
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext


@TransformationRegistry.register('pixelate')
class PixelateTransformation(BaseTransformation):
    """
    Pixelate transformation using downscale algorithm.

    This transformation only downscales the image. Use the 'resize' transformation
    after pixelate to upscale back to desired dimensions.

    Parameters:
        pixel_size (int): Size of each pixel block (default: 8)
    """

    def validate_params(self) -> None:
        """Validate pixelate parameters."""
        pixel_size = self.params.get('pixel_size', 8)

        if not isinstance(pixel_size, int):
            raise ValueError("pixel_size must be an integer")

        if pixel_size < 1:
            raise ValueError("pixel_size must be at least 1")

        if pixel_size > 100:
            raise ValueError("pixel_size must be at most 100")

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Apply pixelation effect by downscaling image.

        Algorithm:
        1. Downscale image by factor of pixel_size using linear interpolation

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Downscaled image
        """
        pixel_size = self.params.get('pixel_size', 8)

        # Get current dimensions
        height, width = image.shape[:2]

        # Calculate new dimensions (downscaled)
        new_width = max(1, width // pixel_size)
        new_height = max(1, height // pixel_size)

        # Downscale
        small = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_LINEAR
        )

        return small
