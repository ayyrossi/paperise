"""
Resize transformation - scales images to target dimensions.
"""

import cv2
import numpy as np
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext


@TransformationRegistry.register('resize')
class ResizeTransformation(BaseTransformation):
    """
    Resize image to target dimensions or back to original size.

    Parameters:
        width (int, optional): Target width in pixels
        height (int, optional): Target height in pixels
        use_original (bool, optional): Use original image dimensions (default: false)
                                       If true, width/height are ignored
        interpolation (str, optional): Interpolation method (default: "nearest")
                                      Options: "nearest", "linear", "cubic", "area"

    Either specify width/height OR set use_original=true.
    """

    # Map string names to OpenCV interpolation constants
    INTERPOLATION_METHODS = {
        'nearest': cv2.INTER_NEAREST,
        'linear': cv2.INTER_LINEAR,
        'cubic': cv2.INTER_CUBIC,
        'area': cv2.INTER_AREA,
    }

    def validate_params(self) -> None:
        """Validate resize parameters."""
        use_original = self.params.get('use_original', False)
        width = self.params.get('width')
        height = self.params.get('height')
        interpolation = self.params.get('interpolation', 'nearest')

        # Must specify either use_original=true OR width+height
        if use_original:
            if width is not None or height is not None:
                raise ValueError(
                    "Cannot specify both use_original=true and width/height. "
                    "Choose one approach."
                )
        else:
            if width is None or height is None:
                raise ValueError(
                    "Must specify both width and height when use_original is false"
                )

            if not isinstance(width, int) or not isinstance(height, int):
                raise ValueError("width and height must be integers")

            if width < 1 or height < 1:
                raise ValueError("width and height must be at least 1")

        # Validate interpolation method
        if interpolation not in self.INTERPOLATION_METHODS:
            valid_methods = ', '.join(self.INTERPOLATION_METHODS.keys())
            raise ValueError(
                f"interpolation must be one of: {valid_methods}, got: {interpolation}"
            )

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Resize image to target dimensions.

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Resized image
        """
        use_original = self.params.get('use_original', False)
        interpolation_name = self.params.get('interpolation', 'nearest')
        interpolation = self.INTERPOLATION_METHODS[interpolation_name]

        if use_original:
            # Use original dimensions from context
            if 'original_width' not in context.metadata or 'original_height' not in context.metadata:
                raise ValueError(
                    "Cannot use original dimensions: not available in context. "
                    "This should not happen - please report as a bug."
                )

            target_width = context.metadata['original_width']
            target_height = context.metadata['original_height']
        else:
            # Use specified dimensions
            target_width = self.params['width']
            target_height = self.params['height']

        # Perform resize
        resized = cv2.resize(
            image,
            (target_width, target_height),
            interpolation=interpolation
        )

        return resized
