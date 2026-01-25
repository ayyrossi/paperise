# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paperise is an image transformation pipeline for wallpaper generation with configurable profiles. It applies a chain of transformations (pixelation, color quantization, dithering, palette replacement, convolution filters) to input images to create retro and artistic effects.

## Running the Application

```bash
# Activate virtual environment (uv-managed)
source .venv/bin/activate

# Basic usage with default profile
python main.py raw/image.jpg processed/output.png

# Specify a profile
python main.py raw/image.jpg processed/output.png --profile retro

# Use custom config file
python main.py input.jpg output.png --config custom_config.yaml --verbose

# List available profiles
grep -A 2 "^  [a-z]" config.yaml | grep -E "^  [a-z]"
```

## Development Commands

```bash
# Run with verbose output for debugging
python main.py input.jpg output.png --profile gameboy --verbose

# Test a single transformation profile
python main.py raw/test.jpg processed/test_profilename.png -p profilename -v
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
   - Context stores auxiliary outputs (palettes, ASCII data) and metadata

3. **Context Pattern**: `TransformationContext` (dataclass) is passed through the entire pipeline to:
   - Store auxiliary outputs (palette files, ASCII art)
   - Share metadata between transformations (e.g., deferred upscaling flag)
   - Enable transformations to communicate with each other

### Performance Optimization via Resize Placement

The pipeline supports performance optimization by controlling when images are resized:
- The `pixelate` transformation only downscales images
- The `resize` transformation upscales back to desired dimensions
- Keeping images small through the pipeline significantly reduces processing time for memory-intensive operations (quantization, dithering)
- Place `resize` at the end of your transformation chain for best performance
- Original dimensions are stored in `context.metadata['original_width']` and `original_height` at pipeline start

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
- Palette outputs are converted to RGB hex format for readability

## Output Files

When transformations produce auxiliary outputs:
- Main output: `output_path` (e.g., `processed/image.png`)
- Palette file: `{stem}_palette.txt` (if `output_palette: true`)
- ASCII art: `{stem}_ascii.png` (if `ascii_output: true`)

## Config File Conventions

Profiles support these transformation types:
- `pixelate`: Downscale for blocky pixel effect (use `resize` afterward to upscale)
- `quantize`: K-means color quantization
- `palette`: Replace colors with custom palette (uses Hungarian algorithm for optimal matching)
- `dither`: Floyd-Steinberg, ordered/Bayer dithering
- `filter`: Arbitrary convolution kernels (edge detect, sharpen, emboss, etc.)
- `resize`: Scale to original dimensions or specific resolution (supports nearest/linear/cubic/area interpolation)
- `border`: Add uniform borders to achieve target resolution (supports hex colors or 1-indexed palette references)
