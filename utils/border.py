"""
Border transformation - adds uniform borders to achieve target resolution.
"""

import cv2
import numpy as np
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext
from utils.io_utils import resolve_color, validate_color_param


@TransformationRegistry.register('border')
class BorderTransformation(BaseTransformation):
    """
    Add uniform borders around image to achieve target resolution.
    Image is centered with borders filling to target dimensions.

    Parameters:
        target_width (int): Final image width including borders
        target_height (int): Final image height including borders
        color: Border color - either:
               - Hex color string (e.g., "#FF5733")
               - Integer (1-indexed) referencing quantize palette color
                 NOTE: Palette indices are 1-indexed, so for 8 colors use 1-8
    """

    def validate_params(self) -> None:
        """Validate border parameters."""
        if 'target_width' not in self.params:
            raise ValueError("border transformation requires 'target_width' parameter")

        if 'target_height' not in self.params:
            raise ValueError("border transformation requires 'target_height' parameter")

        if 'color' not in self.params:
            raise ValueError("border transformation requires 'color' parameter")

        target_width = self.params['target_width']
        target_height = self.params['target_height']
        color = self.params['color']

        if not isinstance(target_width, int):
            raise ValueError("target_width must be an integer")

        if not isinstance(target_height, int):
            raise ValueError("target_height must be an integer")

        if target_width < 1:
            raise ValueError("target_width must be at least 1")

        if target_height < 1:
            raise ValueError("target_height must be at least 1")

        validate_color_param(color, 'color')

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Add borders to image to achieve target resolution.

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Image with borders added
        """
        target_width = self.params['target_width']
        target_height = self.params['target_height']
        color_param = self.params['color']

        # Get current image dimensions
        current_height, current_width = image.shape[:2]
        has_alpha = len(image.shape) == 3 and image.shape[2] == 4

        # Validate that target is larger than current
        if target_width < current_width or target_height < current_height:
            raise ValueError(
                f"Target resolution ({target_width}x{target_height}) must be "
                f"larger than current image size ({current_width}x{current_height})"
            )

        border_color = resolve_color(color_param, context.palette, 'border')

        # Calculate border sizes (uniform on all sides, centered)
        total_border_width = target_width - current_width
        total_border_height = target_height - current_height

        # Distribute borders evenly (favor top/left for odd pixel counts)
        left = total_border_width // 2
        right = total_border_width - left
        top = total_border_height // 2
        bottom = total_border_height - top

        # Add borders using cv2.copyMakeBorder
        bordered = cv2.copyMakeBorder(
            image,
            top, bottom, left, right,
            cv2.BORDER_CONSTANT,
            value=border_color
        )

        return bordered
