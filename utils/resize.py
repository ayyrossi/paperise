"""
Resize transformation - scales images to target dimensions.
"""

import cv2
import numpy as np
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext, CTX_ORIGINAL_WIDTH, CTX_ORIGINAL_HEIGHT


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
        crop_shift_x (float, optional): Horizontal crop position when aspect ratios differ
                                        0.0=left, 0.5=center (default), 1.0=right
        crop_shift_y (float, optional): Vertical crop position when aspect ratios differ
                                        0.0=bottom, 0.5=center (default), 1.0=top

    Either specify width/height OR set use_original=true.
    When the target aspect ratio differs from the source, the image is scaled to cover
    the target and then cropped — never stretched.
    """

    # Map string names to OpenCV interpolation constants
    INTERPOLATION_METHODS = {
        'nearest': cv2.INTER_NEAREST,
        'linear': cv2.INTER_LINEAR,
        'cubic': cv2.INTER_CUBIC,
        'area': cv2.INTER_AREA,
    }

    def validate_params(self) -> None:
        use_original = self.params.get('use_original', False)
        width = self.params.get('width')
        height = self.params.get('height')
        interpolation = self.params.get('interpolation', 'nearest')
        crop_shift_x = self.params.get('crop_shift_x', 0.5)
        crop_shift_y = self.params.get('crop_shift_y', 0.5)

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

        if interpolation not in self.INTERPOLATION_METHODS:
            valid_methods = ', '.join(self.INTERPOLATION_METHODS.keys())
            raise ValueError(
                f"interpolation must be one of: {valid_methods}, got: {interpolation}"
            )

        if not isinstance(crop_shift_x, (int, float)) or not (0.0 <= crop_shift_x <= 1.0):
            raise ValueError("crop_shift_x must be a float between 0.0 and 1.0")
        if not isinstance(crop_shift_y, (int, float)) or not (0.0 <= crop_shift_y <= 1.0):
            raise ValueError("crop_shift_y must be a float between 0.0 and 1.0")

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        use_original = self.params.get('use_original', False)
        interpolation_name = self.params.get('interpolation', 'nearest')
        interpolation = self.INTERPOLATION_METHODS[interpolation_name]
        crop_shift_x = float(self.params.get('crop_shift_x', 0.5))
        crop_shift_y = float(self.params.get('crop_shift_y', 0.5))

        if use_original:
            if CTX_ORIGINAL_WIDTH not in context.metadata or CTX_ORIGINAL_HEIGHT not in context.metadata:
                raise ValueError(
                    "Cannot use original dimensions: not available in context. "
                    "This should not happen - please report as a bug."
                )
            target_width = context.metadata[CTX_ORIGINAL_WIDTH]
            target_height = context.metadata[CTX_ORIGINAL_HEIGHT]
        else:
            target_width = self.params['width']
            target_height = self.params['height']

        src_h, src_w = image.shape[:2]

        # Scale to cover: use the larger scale factor so the image fills the target
        scale = max(target_width / src_w, target_height / src_h)
        scaled_w = round(src_w * scale)
        scaled_h = round(src_h * scale)

        scaled = cv2.resize(image, (scaled_w, scaled_h), interpolation=interpolation)

        # Crop to target if needed
        excess_x = scaled_w - target_width
        excess_y = scaled_h - target_height

        # crop_shift_x: 0=left, 1=right → x_start proportional to excess
        x_start = round(crop_shift_x * excess_x)
        # crop_shift_y: 0=bottom, 1=top → invert so 1.0 means y_start=0
        y_start = round((1.0 - crop_shift_y) * excess_y)

        return scaled[y_start:y_start + target_height, x_start:x_start + target_width]
