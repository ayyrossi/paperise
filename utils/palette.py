"""
Palette replacement transformation using optimal color mapping.
"""

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext
from utils.io_utils import hex_to_bgr


@TransformationRegistry.register('palette')
class PaletteTransformation(BaseTransformation):
    """
    Replace image colors with custom palette using optimal matching.

    Algorithm:
    1. Quantize image to same number of colors as target palette using K-means
    2. Calculate Euclidean distance matrix between quantized colors and palette
    3. Use Hungarian algorithm to find optimal one-to-one color mapping
    4. Replace all pixels with optimally matched palette colors

    Parameters:
        palette (list): List of hex color strings (e.g., ["#FF5733", "#C70039"])
    """

    def validate_params(self) -> None:
        """Validate palette parameters."""
        if 'palette' not in self.params:
            raise ValueError("palette transformation requires 'palette' parameter")

        palette = self.params['palette']

        if not isinstance(palette, list):
            raise ValueError("palette must be a list of hex color strings")

        if len(palette) < 2:
            raise ValueError("palette must contain at least 2 colors")

        if len(palette) > 256:
            raise ValueError("palette must contain at most 256 colors")

        # Validate each hex color
        for color in palette:
            if not isinstance(color, str):
                raise ValueError(f"palette colors must be strings, got: {type(color)}")
            try:
                hex_to_bgr(color)
            except ValueError as e:
                raise ValueError(f"invalid hex color in palette: {color}")

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Apply palette replacement with optimal color mapping.

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Image with colors replaced by palette
        """
        palette_hex = self.params['palette']
        num_colors = len(palette_hex)

        # Convert hex palette to BGR
        target_palette = np.array([hex_to_bgr(color) for color in palette_hex], dtype=np.uint8)

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

        # Step 1: Quantize image to same number of colors as palette
        pixels = image_rgb.reshape(-1, 3).astype(np.float32)

        # Run K-means clustering using cv2
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

        # Run cv2.kmeans
        _, labels, centers = cv2.kmeans(
            pixels,
            num_colors,
            None,
            criteria,
            10,
            cv2.KMEANS_PP_CENTERS
        )

        # Get quantized palette (cluster centers)
        quantized_palette = np.uint8(centers)
        labels = labels.flatten()

        # Step 2: Calculate distance matrix between quantized and target palettes
        # Using Euclidean distance in RGB color space
        # Distance matrix shape: (num_colors, num_colors)
        distance_matrix = np.zeros((num_colors, num_colors))

        for i in range(num_colors):
            for j in range(num_colors):
                # Euclidean distance between colors
                diff = quantized_palette[i].astype(float) - target_palette[j].astype(float)
                distance_matrix[i, j] = np.sqrt(np.sum(diff ** 2))

        # Step 3: Use Hungarian algorithm to find optimal assignment
        # linear_sum_assignment minimizes total distance
        row_indices, col_indices = linear_sum_assignment(distance_matrix)

        # Create mapping from quantized palette indices to target palette indices
        color_mapping = np.zeros(num_colors, dtype=int)
        for row_idx, col_idx in zip(row_indices, col_indices):
            color_mapping[row_idx] = col_idx

        # Step 4: Replace pixels with mapped palette colors
        # Map labels through the optimal assignment
        mapped_labels = color_mapping[labels]
        mapped_pixels = target_palette[mapped_labels]

        # Reshape back to image
        result = mapped_pixels.reshape(height, width, 3)

        # Restore alpha channel if present
        if has_alpha:
            result = np.dstack([result, alpha_channel])

        # Save final palette to context
        context.palette = target_palette.tolist()

        return result.astype(np.uint8)
