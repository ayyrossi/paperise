"""
K-means color quantization transformation.
"""

import cv2
import numpy as np
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext


@TransformationRegistry.register('quantize')
class QuantizeTransformation(BaseTransformation):
    """
    Quantize image colors using K-means clustering.

    The generated palette is always saved to context for use by other transformations
    (e.g., border can reference palette colors by index).

    Parameters:
        num_colors (int): Number of colors in output palette (default: 16)
        output_palette (bool): Write palette to file as {output}_palette.txt (default: false)
    """

    def validate_params(self) -> None:
        """Validate quantization parameters."""
        num_colors = self.params.get('num_colors', 16)

        if not isinstance(num_colors, int):
            raise ValueError("num_colors must be an integer")

        if num_colors < 2:
            raise ValueError("num_colors must be at least 2")

        if num_colors > 256:
            raise ValueError("num_colors must be at most 256")

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Apply K-means color quantization to image.

        Algorithm:
        1. Reshape image to list of pixels
        2. Run K-means clustering on pixel colors
        3. Replace each pixel with its cluster center color
        4. Optionally save palette to context

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Quantized image with reduced color palette
        """
        num_colors = self.params.get('num_colors', 16)
        output_palette = self.params.get('output_palette', False)

        # Get original shape
        original_shape = image.shape
        height, width = original_shape[:2]

        # Handle alpha channel if present
        has_alpha = len(original_shape) == 3 and original_shape[2] == 4
        if has_alpha:
            alpha_channel = image[:, :, 3]
            image_rgb = image[:, :, :3]
        else:
            image_rgb = image

        # Reshape image to list of pixels (H*W, 3)
        pixels = image_rgb.reshape(-1, 3).astype(np.float32)

        # Run K-means clustering using cv2
        # Define termination criteria (type, max_iter, epsilon)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

        # Run cv2.kmeans
        # Returns: (compactness, labels, centers)
        _, labels, centers = cv2.kmeans(
            pixels,                      # 2D float32 array
            num_colors,                  # K (number of clusters)
            None,                        # bestLabels (None for new)
            criteria,                    # termination criteria
            10,                          # attempts (number of times to run)
            cv2.KMEANS_PP_CENTERS        # initialization method (kmeans++)
        )

        # Get cluster centers (palette)
        palette = np.uint8(centers)

        # Flatten labels for indexing
        labels = labels.flatten()

        # Replace pixels with cluster centers
        quantized_pixels = palette[labels]

        # Reshape back to image
        quantized = quantized_pixels.reshape(height, width, 3)

        # Restore alpha channel if present
        if has_alpha:
            quantized = np.dstack([quantized, alpha_channel])

        # Always save palette to context (for use by other transformations)
        context.palette = palette.tolist()

        # Mark whether palette file should be written
        if output_palette:
            context.metadata['output_palette_file'] = True

        return quantized.astype(np.uint8)
