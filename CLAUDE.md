# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paperise is an image transformation pipeline for wallpaper generation with configurable profiles. It applies a chain of transformations (pixelation, color quantization, dithering, palette replacement, ASCII art, convolution filters) to input images to create retro and artistic effects.

## Running the Application

```bash
# Basic usage with default profile
uv run python main.py raw/image.jpg processed/output.png

# Specify a profile
uv run python main.py raw/image.jpg processed/output.png --profile retro

# Use custom config file
uv run python main.py input.jpg output.png --config custom_config.yaml --verbose

# List available profiles
grep -A 2 "^  [a-z]" config.yaml | grep -E "^  [a-z]"
```

## Development Commands

```bash
# Run with verbose output for debugging
uv run python main.py input.jpg output.png --profile gameboy --verbose

# Test a single transformation profile
uv run python main.py raw/test.jpg processed/test_profilename.png -p profilename -v
```

## Architecture

### Transformation Pipeline Pattern

The codebase uses a **registry pattern with decorator-based registration** for transformations:

1. **Registry (`utils/base.py`)**: `TransformationRegistry` maintains a global registry of all available transformations. Transformation classes self-register using the `@TransformationRegistry.register('name')` decorator.

2. **Pipeline Execution (`main.py`)**:
   - Loads profile configuration from YAML
   - Imports `utils` package (triggers all transformation registration via `utils/__init__.py`)
   - Retrieves transformation classes from registry by name
   - Executes transformations sequentially, passing both image and context between stages
   - On PNG output, embeds pipeline metadata and the final palette (if any) as PNG text chunks

3. **Context Pattern**: `TransformationContext` (dataclass) is passed through the entire pipeline to:
   - Store the active palette (`context.palette`): a list of BGR tuples, updated by `quantize` and `palette` transformations and consumed by `border` and `ascii` for color resolution
   - Share metadata between transformations via `context.metadata` (keyed by constants in `utils/base.py`)
   - Enable transformations to communicate with each other

### Context Metadata Keys

Defined as constants in `utils/base.py`:

| Constant | Key | Set by | Used by |
|---|---|---|---|
| `CTX_ORIGINAL_WIDTH` | `"original_width"` | `main.py` at startup | `resize` |
| `CTX_ORIGINAL_HEIGHT` | `"original_height"` | `main.py` at startup | `resize` |
| `CTX_VERBOSE` | `"verbose"` | `main.py` at startup | `ascii` |

### Color Resolution

`utils/io_utils.py` provides two shared helpers used by any transformation that accepts a color parameter:

- `validate_color_param(value, param_name)`: validates a hex string or 1-indexed integer palette reference
- `resolve_color(color_param, palette, context_name)`: resolves to a BGR tuple at runtime — hex strings are parsed directly, integers index into `context.palette` (1-indexed)

### Performance Optimization via Resize Placement

The pipeline supports performance optimization by controlling when images are resized:
- The `pixelate` transformation only downscales images
- The `resize` transformation upscales back to desired dimensions
- Keeping images small through the pipeline significantly reduces processing time for memory-intensive operations (quantization, dithering)
- Place `resize` at the end of your transformation chain for best performance
- Original dimensions are stored via `CTX_ORIGINAL_WIDTH` / `CTX_ORIGINAL_HEIGHT` at pipeline start

### Adding New Transformations

1. Create new file in `utils/` (e.g., `utils/blur.py`)
2. Inherit from `BaseTransformation` and use `@TransformationRegistry.register('name')` decorator
3. Implement `apply(image, context)` method (receives BGR numpy array from OpenCV)
4. Optionally implement `validate_params()` for parameter validation
5. Import in `utils/__init__.py` to trigger registration
6. Add profile entries in `config.yaml`

Example skeleton:
```python
from utils.base import BaseTransformation, TransformationRegistry, TransformationContext

@TransformationRegistry.register('blur')
class BlurTransformation(BaseTransformation):
    def validate_params(self):
        # Validate self.params dictionary
        pass

    def apply(self, image: np.ndarray, context: TransformationContext):
        # Transform image (BGR format)
        # Update context if needed (context.palette, context.metadata, etc.)
        return transformed_image
```

### Profile Configuration Structure

Each profile in `config.yaml` defines:
- `transformations`: Ordered list of transformation names (executed sequentially)
- `parameters`: Dictionary mapping transformation names to their parameter dictionaries

Transformations are applied in the order specified in the profile's `transformations` list.

## Image Format Notes

- OpenCV is used for core image operations (loads images in **BGR format**, not RGB)
- All transformations receive and return BGR numpy arrays
- Alpha channels are preserved when present
- Palette colors stored in context and PNG metadata are in BGR order; they are converted to RGB hex when written to PNG text chunks

## Output Files

All output is written to a single file: `output_path` (e.g., `processed/image.png`).

For PNG outputs, the following metadata is embedded as text chunks:
- `paperise:profile` — profile name
- `paperise:pipeline` — JSON array of transformation names
- `paperise:params` — JSON object of transformation parameters
- `paperise:timestamp` — UTC ISO 8601 timestamp
- `paperise:palette` — JSON array of RGB hex strings (if a palette was generated)

## Config File Conventions

### Global Settings (`settings:`)
- `image_extensions`: File extensions treated as images during directory batch processing
- `font_fallback_paths`: Ordered list of font file paths to try when a named font cannot be resolved via `fc-match` (used by the `ascii` transformation)

### Transformation Types

- `pixelate`: Downscale for blocky pixel effect (use `resize` afterward to upscale)
- `quantize`: K-means color quantization
  - `num_colors` (int, default 16): palette size (2–256)
  - `color_space` (str, default `cielab`): clustering color space — `rgb`, `cmyk`, `cielab`, `hsl`, `hsv`
  - `distance_metric` (str, default `euclidean`): `euclidean` (uses OpenCV, fast), `manhattan`, `cosine` (custom K-means++ implementation)
- `palette`: Replace colors with a custom hex palette using the Hungarian algorithm for optimal matching
- `dither`: Floyd-Steinberg, ordered, or Bayer dithering
  - `dither_type`: `floyd_steinberg`, `ordered`, `bayer`
  - `amount` (float, 0–1): dithering strength
- `ascii`: Render image as colored ASCII art — each source pixel becomes one character, colored to match
  - `chars` (str): character ramp, darkest to brightest (default: `" .:-=+*#%@"`)
  - `font` (str): font name (resolved via `fc-match`) or path to TTF file
  - `font_size` (int): font size in points
  - `background`: background color — hex string or 1-indexed palette reference
  - `char_aspect_ratio` (float): character width/height ratio (default 0.6)
  - Works best on pixelated/downsampled images; place after `pixelate` and before `resize`
- `filter`: Arbitrary convolution kernels (edge detect, sharpen, emboss, etc.)
- `resize`: Scale to original dimensions or specific resolution
  - `use_original` (bool): restore to pre-pipeline dimensions
  - `width` / `height` (int): explicit target size
  - `interpolation`: `nearest`, `linear`, `cubic`, `area`
- `border`: Add uniform borders to achieve a target resolution
  - `target_width` / `target_height` (int): final canvas size
  - `color`: hex string or 1-indexed palette reference
