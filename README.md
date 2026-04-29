# Paperise

A powerful image transformation pipeline for creating retro and artistic wallpapers with configurable profiles. Apply pixelation, color quantization, dithering, ASCII art, filters, and more to transform images into unique aesthetic styles.

## Features

- **Modular Pipeline**: Chain together transformations in any order
- **Multiple Color Spaces**: Quantize colors in RGB, CMYK, CIE L\*a\*b\*, HSL, or HSV
- **Distance Metrics**: Choose between Euclidean, Manhattan, or Cosine distance for K-means clustering
- **Dithering**: Floyd-Steinberg and Bayer/ordered dithering support
- **ASCII Art**: Render images as colored ASCII characters
- **Custom Palettes**: Replace colors with predefined palettes using optimal matching
- **Convolution Filters**: Apply arbitrary kernels for effects like sharpen, blur, edge detect
- **Profile-Based**: Save and reuse transformation chains via YAML configuration

## Installation

Paperise uses [uv](https://github.com/astral-sh/uv) for Python package management:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd paperise

# Dependencies are managed by uv automatically
```

## Quick Start

```bash
# Basic usage with default profile
uv run python main.py input.jpg output.png

# Specify a profile
uv run python main.py input.jpg output.png --profile retro

# Use custom config file with verbose output
uv run python main.py input.jpg output.png --config my_config.yaml --verbose

# List available profiles
grep "^  [a-z]" config.yaml
```

## Usage

```
uv run python main.py [OPTIONS] INPUT_PATH OUTPUT_PATH

Options:
  -p, --profile TEXT    Profile name from config file (default: "default")
  -c, --config PATH     Path to configuration file (default: "config.yaml")
  -v, --verbose         Enable verbose output
  --help                Show help message
```

## Configuration File Structure

The `config.yaml` file defines transformation profiles. Each profile specifies:

```yaml
profiles:
  profile_name:
    transformations: [transform1, transform2, ...]  # Executed in order
    parameters:
      transform1:
        param1: value1
        param2: value2
      transform2:
        param1: value1
```

### Example Profile

```yaml
profiles:
  retro:
    transformations: [pixelate, quantize, dither, resize]
    parameters:
      pixelate:
        pixel_size: 8
      quantize:
        num_colors: 16
        color_space: cielab
        distance_metric: euclidean
        output_palette: true
      dither:
        dither_type: floyd_steinberg
        amount: 0.8
      resize:
        use_original: true
```

## Available Transformations

### 1. Pixelate

Creates a blocky retro pixel aesthetic by downscaling the image. Use `resize` after this to upscale back to desired dimensions.

**Parameters:**
- `pixel_size` (int, default: 8): Size of each pixel block (1-100)

**Example:**
```yaml
pixelate:
  pixel_size: 16
```

---

### 2. Quantize

Reduces the number of colors using K-means clustering with configurable color spaces and distance metrics.

**Parameters:**
- `num_colors` (int, default: 16): Number of colors in output palette (2-256)
- `color_space` (str, default: "cielab"): Color space for clustering
  - `"rgb"` - Standard RGB color space
  - `"cmyk"` - CMYK (Cyan, Magenta, Yellow, Key/Black) color space
  - `"cielab"` - Perceptually uniform CIE L\*a\*b\* color space (recommended)
  - `"hsl"` - Hue, Saturation, Lightness
  - `"hsv"` - Hue, Saturation, Value
- `distance_metric` (str, default: "euclidean"): Distance calculation method
  - `"euclidean"` - Standard Euclidean distance (fastest, uses OpenCV)
  - `"manhattan"` - Manhattan/L1 distance
  - `"cosine"` - Cosine distance
- `output_palette` (bool, default: false): Save palette to `{output}_palette.txt`

**Example:**
```yaml
quantize:
  num_colors: 32
  color_space: hsv
  distance_metric: manhattan
  output_palette: true
```

**Notes:**
- The generated palette is always saved to context for use by other transformations (border, ascii)
- CIE L\*a\*b\* color space provides perceptually uniform results
- HSV/HSL work well for images where hue preservation matters
- Manhattan and cosine distances may produce different clustering results than Euclidean

---

### 3. Palette

Replaces image colors with a custom palette using optimal color matching via the Hungarian algorithm.

**Parameters:**
- `palette` (list of strings, required): List of hex color strings

**Example:**
```yaml
palette:
  palette:
    - "#FF00FF"  # Magenta
    - "#00FFFF"  # Cyan
    - "#FFFF00"  # Yellow
    - "#000000"  # Black
```

**Notes:**
- Quantizes image to same number of colors as palette, then optimally maps colors
- Automatically outputs palette file
- Palette must contain 2-256 colors

---

### 4. Dither

Applies dithering to create retro halftone effects and smooth color transitions.

**Parameters:**
- `dither_type` (str, required): Type of dithering algorithm
  - `"floyd_steinberg"` - Error diffusion dithering (higher quality)
  - `"ordered"` - Bayer matrix ordered dithering (retro look)
  - `"bayer"` - Alias for ordered
- `amount` (float, default: 1.0): Dithering strength (0.0-1.0)

**Example:**
```yaml
dither:
  dither_type: floyd_steinberg
  amount: 0.8
```

**Notes:**
- Floyd-Steinberg produces smoother gradients
- Ordered/Bayer dithering creates a distinctive retro pattern
- Lower amounts produce subtler effects

---

### 5. ASCII

Renders the image as colored ASCII art. Each pixel becomes an ASCII character colored to match the pixel's color.

**Parameters:**
- `chars` (str, default: " .:-=+*#%@"): Characters to use from darkest to brightest
- `font` (str, default: "monospace"): Font name or path to TTF file
- `font_size` (int, default: 12): Font size in points
- `background` (str or int, default: "#000000"): Background color
  - Hex color string (e.g., `"#000000"`)
  - Integer (1-indexed) referencing quantize palette color
- `char_aspect_ratio` (float, default: 0.6): Character width/height ratio for spacing

**Example:**
```yaml
ascii:
  chars: " .:-=+*#%@"
  font: "DepartureMono Nerd Font"
  font_size: 48
  background: "#000000"
  char_aspect_ratio: 0.6
```

**Notes:**
- Works best with pixelated/downsampled images
- Font must be monospace for best results
- Background can reference palette colors: use integer 1-N for N-color palette
- Significantly increases image resolution

---

### 6. Filter

Applies arbitrary convolution filters using custom kernels.

**Parameters:**
- `kernel` (2D list, required): Square matrix with odd dimensions (e.g., 3x3, 5x5)

**Common Kernels:**

**Sharpen:**
```yaml
filter:
  kernel:
    - [ 0, -1,  0]
    - [-1,  5, -1]
    - [ 0, -1,  0]
```

**Edge Detect:**
```yaml
filter:
  kernel:
    - [-1, -1, -1]
    - [-1,  8, -1]
    - [-1, -1, -1]
```

**Emboss:**
```yaml
filter:
  kernel:
    - [-2, -1,  0]
    - [-1,  1,  1]
    - [ 0,  1,  2]
```

**Blur (3x3):**
```yaml
filter:
  kernel:
    - [1, 1, 1]
    - [1, 1, 1]
    - [1, 1, 1]
```

**Notes:**
- Kernel must be square with odd dimensions
- All values must be numbers (int or float)
- Blur kernels are automatically normalized by OpenCV

---

### 7. Resize

Scales the image to target dimensions or back to original size.

**Parameters:**
- `width` (int, optional): Target width in pixels
- `height` (int, optional): Target height in pixels
- `use_original` (bool, default: false): Use original image dimensions
- `interpolation` (str, default: "nearest"): Interpolation method
  - `"nearest"` - Nearest neighbor (blocky, retro look)
  - `"linear"` - Bilinear interpolation
  - `"cubic"` - Bicubic interpolation (smooth, high quality)
  - `"area"` - Resampling using pixel area relation

**Example (restore original size):**
```yaml
resize:
  use_original: true
  interpolation: nearest
```

**Example (specific dimensions):**
```yaml
resize:
  width: 1920
  height: 1080
  interpolation: cubic
```

**Notes:**
- Either specify `width`/`height` OR set `use_original: true`
- Use `nearest` interpolation to preserve pixelated look
- Place resize at end of pipeline for best performance

---

### 8. Border

Adds uniform borders around the image to achieve a target resolution. Image is centered with borders filling to target dimensions.

**Parameters:**
- `target_width` (int, required): Final image width including borders
- `target_height` (int, required): Final image height including borders
- `color` (str or int, required): Border color
  - Hex color string (e.g., `"#FF5733"`)
  - Integer (1-indexed) referencing quantize palette color

**Example (hex color):**
```yaml
border:
  target_width: 1920
  target_height: 1080
  color: "#000000"
```

**Example (palette reference):**
```yaml
border:
  target_width: 1920
  target_height: 1080
  color: 1  # First color from quantize palette
```

**Notes:**
- Target resolution must be larger than current image size
- Palette indices are 1-indexed: for 8 colors, valid indices are 1-8
- Requires quantize or palette transformation to run first when using palette reference

---

## Pipeline Design Best Practices

### Performance Optimization

Keep images small through the pipeline for better performance:

1. Start with `pixelate` to downscale the image
2. Apply memory-intensive operations (quantize, dither) on small image
3. Place `resize` at the end to upscale to final dimensions

**Example:**
```yaml
transformations: [pixelate, quantize, dither, resize]
```

### Palette-Based Workflows

When using border or ascii with palette references, ensure quantize or palette runs first:

```yaml
transformations: [pixelate, quantize, dither, resize, border]
parameters:
  quantize:
    num_colors: 8
  border:
    color: 1  # References first palette color
```

### Transformation Order Matters

Transformations are applied sequentially. Different orders produce different results:

```yaml
# Sharp pixel edges
transformations: [quantize, pixelate, resize]

# Smoothed pixel edges
transformations: [pixelate, quantize, resize]

# Dithering before quantization has no effect
transformations: [dither, quantize]  # Wrong!

# Dithering after quantization works correctly
transformations: [quantize, dither]  # Correct!
```

## Example Profiles

### 8-bit Retro
```yaml
retro:
  transformations: [pixelate, quantize, dither, resize]
  parameters:
    pixelate:
      pixel_size: 8
    quantize:
      num_colors: 16
      output_palette: true
    dither:
      dither_type: floyd_steinberg
      amount: 0.8
    resize:
      use_original: true
```

### Monochrome with Border
```yaml
monochrome:
  transformations: [pixelate, quantize, dither, resize, border]
  parameters:
    pixelate:
      pixel_size: 8
    quantize:
      num_colors: 2
    dither:
      dither_type: floyd_steinberg
      amount: 1.0
    resize:
      use_original: true
    border:
      target_width: 1920
      target_height: 1080
      color: 1
```

### ASCII Art
```yaml
ascii_art:
  transformations: [pixelate, quantize, ascii]
  parameters:
    pixelate:
      pixel_size: 16
    quantize:
      num_colors: 32
    ascii:
      chars: " .:-=+*#%@"
      font: "DepartureMono Nerd Font"
      font_size: 48
```

### Custom Palette
```yaml
gameboy:
  transformations: [pixelate, quantize, palette, dither, resize]
  parameters:
    pixelate:
      pixel_size: 4
    quantize:
      num_colors: 4
    palette:
      palette:
        - "#0f380f"  # Darkest green
        - "#306230"  # Dark green
        - "#8bac0f"  # Light green
        - "#9bbc0f"  # Lightest green
    dither:
      dither_type: floyd_steinberg
      amount: 0.5
    resize:
      use_original: true
```

### HSV Color Space with Manhattan Distance
```yaml
quantize_hsv_manhattan:
  transformations: [pixelate, quantize, dither, resize]
  parameters:
    pixelate:
      pixel_size: 8
    quantize:
      num_colors: 24
      color_space: hsv
      distance_metric: manhattan
      output_palette: true
    dither:
      dither_type: ordered
      amount: 0.6
    resize:
      use_original: true
```

### Phone Wallpaper (crop-positioned resize)
```yaml
wallpaper_a53:
  transformations: [pixelate, dither, palette, resize, border]
  parameters:
    pixelate:
      pixel_size: 2
    dither:
      dither_type: floyd_steinberg
      amount: 0.8
    palette:
      palette:
        - "#11111b"
        - "#f38ba8"
    resize:
      width: 880
      height: 1900
      crop_shift_x: 0.85   # bias crop toward right side of image
    border:
      target_width: 1080
      target_height: 2400
      color: "#11111b"
```

## Output Files

When processing `input.jpg` to `output.png`:
- **Main output**: `output.png` (transformed image)
- **Palette file**: `output_palette.txt` (if `output_palette: true` or using palette transformation)

Palette files contain hex color codes (one per line):
```
#FF5733
#C70039
#900C3F
...
```

## Color Spaces and Distance Metrics

Different color spaces and distance metrics can significantly affect quantization results:

- **CIE L\*a\*b\*** (default): Perceptually uniform, good for general use
- **RGB**: Simple, fast, but not perceptually uniform
- **HSV/HSL**: Preserves hue relationships, good for colorful images
- **CMYK**: Print-oriented color space

Distance metrics:
- **Euclidean** (default): Standard distance, fast (uses OpenCV)
- **Manhattan**: Sum of absolute differences, can produce different clustering
- **Cosine**: Angular distance, useful for color direction similarity

Experiment with different combinations to achieve desired aesthetic effects.

## Contributing

Contributions are welcome! The codebase uses a registry pattern for transformations:

1. Create new transformation in `utils/your_transform.py`
2. Inherit from `BaseTransformation`
3. Use `@TransformationRegistry.register('name')` decorator
4. Implement `validate_params()` and `apply(image, context)` methods
5. Import in `utils/__init__.py`

See `CLAUDE.md` for detailed architecture documentation.

## License

[Add your license here]

## Credits

Built with OpenCV, NumPy, Pillow, and SciPy.
