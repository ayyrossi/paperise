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
    (e.g., border can reference palette colors by index) and embedded in PNG metadata.

    Parameters:
        num_colors (int): Number of colors in output palette (default: 16)
        color_space (str): Color space for clustering - 'rgb', 'cmyk', 'cielab', 'hsl', 'hsv' (default: 'cielab')
        distance_metric (str): Distance metric - 'euclidean', 'manhattan', 'cosine' (default: 'euclidean')
    """

    def validate_params(self) -> None:
        """Validate quantization parameters."""
        num_colors = self.params.get('num_colors', 16)
        color_space = self.params.get('color_space', 'cielab').lower()
        distance_metric = self.params.get('distance_metric', 'euclidean').lower()

        if not isinstance(num_colors, int):
            raise ValueError("num_colors must be an integer")

        if num_colors < 2:
            raise ValueError("num_colors must be at least 2")

        if num_colors > 256:
            raise ValueError("num_colors must be at most 256")

        valid_color_spaces = ['rgb', 'cmyk', 'cielab', 'hsl', 'hsv']
        if color_space not in valid_color_spaces:
            raise ValueError(f"color_space must be one of {valid_color_spaces}")

        valid_distance_metrics = ['euclidean', 'manhattan', 'cosine']
        if distance_metric not in valid_distance_metrics:
            raise ValueError(f"distance_metric must be one of {valid_distance_metrics}")

    def _convert_to_color_space(self, image_bgr: np.ndarray, color_space: str) -> np.ndarray:
        """
        Convert BGR image to specified color space.

        Args:
            image_bgr: Input image in BGR format
            color_space: Target color space

        Returns:
            Image in target color space (H, W, channels)
        """
        if color_space == 'rgb':
            # Simple BGR to RGB swap
            return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        elif color_space == 'cmyk':
            # BGR -> RGB -> CMYK
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            k = 1 - np.max(rgb, axis=2, keepdims=True)
            # Avoid division by zero
            k_safe = np.where(k == 1, 1, k)
            c = (1 - rgb[:, :, 0:1] - k) / (1 - k_safe)
            m = (1 - rgb[:, :, 1:2] - k) / (1 - k_safe)
            y = (1 - rgb[:, :, 2:3] - k) / (1 - k_safe)
            # Scale to 0-100 range for better clustering
            cmyk = np.concatenate([c, m, y, k], axis=2) * 100
            return cmyk
        elif color_space == 'cielab':
            return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        elif color_space == 'hsl':
            return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HLS)
        elif color_space == 'hsv':
            return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        else:
            raise ValueError(f"Unknown color space: {color_space}")

    def _convert_from_color_space(self, image: np.ndarray, color_space: str) -> np.ndarray:
        """
        Convert image from specified color space back to BGR.

        Args:
            image: Image in specified color space
            color_space: Source color space

        Returns:
            Image in BGR format
        """
        if color_space == 'rgb':
            return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2BGR)
        elif color_space == 'cmyk':
            # CMYK -> RGB -> BGR (scale back from 0-100 to 0-1)
            cmyk = image.astype(np.float32) / 100.0
            c, m, y, k = cmyk[:, :, 0], cmyk[:, :, 1], cmyk[:, :, 2], cmyk[:, :, 3]
            r = (1 - c) * (1 - k)
            g = (1 - m) * (1 - k)
            b = (1 - y) * (1 - k)
            rgb = np.stack([r, g, b], axis=2)
            rgb = np.clip(rgb * 255, 0, 255).astype(np.uint8)
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        elif color_space == 'cielab':
            return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_LAB2BGR)
        elif color_space == 'hsl':
            return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_HLS2BGR)
        elif color_space == 'hsv':
            return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_HSV2BGR)
        else:
            raise ValueError(f"Unknown color space: {color_space}")

    def _compute_distance(self, points: np.ndarray, centers: np.ndarray, metric: str) -> np.ndarray:
        """
        Compute distance between points and cluster centers.

        Args:
            points: Array of shape (N, D) - N points in D dimensions
            centers: Array of shape (K, D) - K cluster centers
            metric: Distance metric to use

        Returns:
            Distance matrix of shape (N, K)
        """
        if metric == 'euclidean':
            # Vectorized Euclidean distance
            # Using broadcasting: (N, 1, D) - (1, K, D) -> (N, K, D)
            diff = points[:, np.newaxis, :] - centers[np.newaxis, :, :]
            distances = np.sqrt(np.sum(diff ** 2, axis=2))
            return distances
        elif metric == 'manhattan':
            # Manhattan (L1) distance
            diff = points[:, np.newaxis, :] - centers[np.newaxis, :, :]
            distances = np.sum(np.abs(diff), axis=2)
            return distances
        elif metric == 'cosine':
            # Cosine distance: 1 - cosine_similarity
            # Normalize points and centers
            points_norm = points / (np.linalg.norm(points, axis=1, keepdims=True) + 1e-10)
            centers_norm = centers / (np.linalg.norm(centers, axis=1, keepdims=True) + 1e-10)
            # Compute cosine similarity via dot product
            similarity = np.dot(points_norm, centers_norm.T)
            distances = 1 - similarity
            return distances
        else:
            raise ValueError(f"Unknown distance metric: {metric}")

    def _kmeans_custom(self, pixels: np.ndarray, num_colors: int, metric: str, max_iter: int = 10) -> tuple:
        """
        Custom K-means implementation with configurable distance metrics.

        Args:
            pixels: Array of shape (N, D) - pixel values
            num_colors: Number of clusters
            metric: Distance metric to use
            max_iter: Maximum iterations

        Returns:
            Tuple of (labels, centers)
        """
        N, D = pixels.shape

        # Initialize centers using K-means++ algorithm
        centers = np.zeros((num_colors, D), dtype=np.float32)

        # First center: random point
        centers[0] = pixels[np.random.randint(N)]

        # Remaining centers: weighted by distance to nearest existing center
        for i in range(1, num_colors):
            distances = self._compute_distance(pixels, centers[:i], metric)
            min_distances = np.min(distances, axis=1)
            # Square distances for K-means++ weighting
            probabilities = min_distances ** 2
            probabilities /= probabilities.sum()
            centers[i] = pixels[np.random.choice(N, p=probabilities)]

        # K-means iterations
        labels = np.zeros(N, dtype=np.int32)

        for iteration in range(max_iter):
            # Assign points to nearest center
            distances = self._compute_distance(pixels, centers, metric)
            new_labels = np.argmin(distances, axis=1)

            # Check convergence
            if np.array_equal(labels, new_labels):
                break
            labels = new_labels

            # Update centers (mean of assigned points)
            for k in range(num_colors):
                mask = labels == k
                if np.any(mask):
                    centers[k] = np.mean(pixels[mask], axis=0)

        return labels, centers

    def apply(self, image: np.ndarray, context: TransformationContext) -> np.ndarray:
        """
        Apply K-means color quantization to image.

        Algorithm:
        1. Convert image to specified color space
        2. Reshape to list of pixels
        3. Run K-means clustering using specified distance metric
        4. Replace each pixel with its cluster center color
        5. Convert back to BGR and save palette to context

        Args:
            image: Input image (BGR format)
            context: Transformation context

        Returns:
            Quantized image with reduced color palette
        """
        num_colors = self.params.get('num_colors', 16)
        color_space = self.params.get('color_space', 'cielab').lower()
        distance_metric = self.params.get('distance_metric', 'euclidean').lower()

        # Get original shape
        original_shape = image.shape
        height, width = original_shape[:2]

        # Handle alpha channel if present
        has_alpha = len(original_shape) == 3 and original_shape[2] == 4
        if has_alpha:
            alpha_channel = image[:, :, 3]
            image_bgr = image[:, :, :3]
        else:
            image_bgr = image

        # Convert to target color space
        image_colorspace = self._convert_to_color_space(image_bgr, color_space)

        # Reshape image to list of pixels (H*W, channels)
        pixels = image_colorspace.reshape(-1, image_colorspace.shape[2]).astype(np.float32)

        # Run K-means clustering
        if distance_metric == 'euclidean':
            # Use fast OpenCV implementation for Euclidean distance
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(
                pixels,
                num_colors,
                None,
                criteria,
                10,  # attempts
                cv2.KMEANS_PP_CENTERS
            )
            labels = labels.flatten()
        else:
            # Use custom implementation for Manhattan/Cosine distance
            labels, centers = self._kmeans_custom(pixels, num_colors, distance_metric, max_iter=10)

        # Replace pixels with cluster centers
        quantized_pixels = centers[labels]

        # Reshape back to image
        quantized_colorspace = quantized_pixels.reshape(height, width, -1)

        # Convert back to BGR
        quantized_bgr = self._convert_from_color_space(quantized_colorspace, color_space)

        # Restore alpha channel if present
        if has_alpha:
            quantized = np.dstack([quantized_bgr, alpha_channel])
        else:
            quantized = quantized_bgr

        # Convert palette centers back to BGR for storage
        # Create a dummy image with palette colors to convert back
        palette_colorspace = centers.reshape(1, num_colors, -1)
        palette_bgr = self._convert_from_color_space(palette_colorspace, color_space)
        palette = palette_bgr.reshape(num_colors, 3)

        # Save palette to context (for use by other transformations and PNG metadata)
        context.palette = palette.tolist()

        return quantized.astype(np.uint8)
