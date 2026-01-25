"""
Arbitrary convolution filter transformation.
"""

import cv2
import numpy as np
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext


@TransformationRegistry.register('filter')
class FilterTransformation(BaseTransformation):
    """
    Apply arbitrary convolution filter using custom kernel.

    Parameters:
        kernel (list): 2D list representing convolution kernel
                      Example: [[0, -1, 0], [-1, 5, -1], [0, -1, 0]] for sharpening

    Common kernels:
        - Sharpen: [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
        - Edge detect: [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]
        - Blur: [[1, 1, 1], [1, 1, 1], [1, 1, 1]] (will be normalized)
        - Emboss: [[-2, -1, 0], [-1, 1, 1], [0, 1, 2]]
    """

    def validate_params(self) -> None:
        """Validate filter parameters."""
        if 'kernel' not in self.params:
            raise ValueError("filter transformation requires 'kernel' parameter")

        kernel = self.params['kernel']

        if not isinstance(kernel, list):
            raise ValueError("kernel must be a 2D list")

        if len(kernel) == 0:
            raise ValueError("kernel cannot be empty")

        # Check that all rows have the same length
        row_length = len(kernel[0])
        for row in kernel:
            if not isinstance(row, list):
                raise ValueError("kernel must be a 2D list")
            if len(row) != row_length:
                raise ValueError("all kernel rows must have the same length")

        # Check that kernel is square
        if len(kernel) != row_length:
            raise ValueError("kernel must be square (NxN)")

        # Check that kernel has odd dimensions
        if len(kernel) % 2 == 0:
            raise ValueError("kernel dimensions must be odd (e.g., 3x3, 5x5)")

        # Check that all values are numbers
        for row in kernel:
            for val in row:
                if not isinstance(val, (int, float)):
                    raise ValueError("all kernel values must be numbers")

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Apply convolution filter to image.

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Filtered image
        """
        kernel = self.params['kernel']

        # Convert kernel to numpy array
        kernel_array = np.array(kernel, dtype=np.float32)

        # Apply filter using cv2.filter2D
        # -1 means output will have same depth as input
        filtered = cv2.filter2D(image, -1, kernel_array)

        return filtered
