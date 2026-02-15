"""
Paperise - Wallpaper Generation Application
Image transformation pipeline with configurable profiles.
"""

import sys
from pathlib import Path

import click
import cv2
import numpy as np
import yaml
from PIL import Image

from utils.base import TransformationRegistry, TransformationContext
from utils.io_utils import load_image, save_palette
from utils.metadata import build_pnginfo, read_metadata, save_profile_to_config


def _save_image(image: np.ndarray, output_path: str, pnginfo=None) -> None:
    """
    Save image to disk. For PNG outputs with metadata, use Pillow so the
    PngInfo text chunks are embedded. For all other formats fall back to OpenCV.
    """
    if Path(output_path).suffix.lower() == ".png" and pnginfo is not None:
        # Convert BGR (OpenCV) → RGB (Pillow)
        if image.shape[2] == 4:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
            pil_image = Image.fromarray(rgb, "RGBA")
        else:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb, "RGB")
        pil_image.save(output_path, pnginfo=pnginfo)
    else:
        success = cv2.imwrite(output_path, image)
        if not success:
            raise ValueError(f"Could not save image to: {output_path}")


def _process_single_image(
    input_path: str,
    output_path: str,
    transformations: list,
    parameters: dict,
    active_profile: str,
    verbose: bool,
) -> None:
    """Load, transform, and save a single image."""
    if verbose:
        click.echo(f"Loading image: {input_path}")

    image = load_image(input_path)

    if verbose:
        click.echo(f"Image size: {image.shape[1]}x{image.shape[0]}")

    context = TransformationContext()
    context.metadata["original_width"] = image.shape[1]
    context.metadata["original_height"] = image.shape[0]

    for trans_name in transformations:
        if verbose:
            click.echo(f"Applying transformation: {trans_name}")

        try:
            trans_class = TransformationRegistry.get(trans_name)
        except KeyError as e:
            available = ", ".join(TransformationRegistry.list_transformations())
            click.echo(
                f"Error: {e}\nAvailable transformations: {available}", err=True
            )
            sys.exit(1)

        trans_params = parameters.get(trans_name, {})
        transformation = trans_class(trans_params)
        transformation.validate_params()
        image = transformation.apply(image, context)

        if verbose:
            click.echo(f"  → Output size: {image.shape[1]}x{image.shape[0]}")

    if verbose:
        click.echo(f"Saving image: {output_path}")

    pnginfo = None
    if Path(output_path).suffix.lower() == ".png":
        pnginfo = build_pnginfo(active_profile, transformations, parameters)

    _save_image(image, output_path, pnginfo=pnginfo)

    output_dir = Path(output_path).parent
    output_stem = Path(output_path).stem

    if context.palette and context.metadata.get("output_palette_file", False):
        palette_path = output_dir / f"{output_stem}_palette.txt"
        if verbose:
            click.echo(f"Saving palette: {palette_path}")
        save_palette(context.palette, str(palette_path))

    click.echo(f"✓ Successfully processed image: {output_path}")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_path", required=False, default=None)
@click.argument("output_path", required=False, default=None)
@click.option("--profile", "-p", default="default", help="Profile name from config file")
@click.option(
    "--config",
    "-c",
    default="config.yaml",
    type=click.Path(),
    help="Path to configuration file",
)
@click.option(
    "--from-image",
    "from_image",
    default=None,
    type=click.Path(exists=True),
    help="Replay the pipeline embedded in this image instead of using --profile",
)
@click.option(
    "--extract-profile",
    "extract_profile",
    default=None,
    type=click.Path(exists=True),
    help="Extract embedded pipeline from image and save to config (no image processing)",
)
@click.option(
    "--save-as",
    "save_as",
    default=None,
    help="Profile name to use when saving an extracted profile (required with --extract-profile)",
)
@click.option(
    "--output-config",
    "output_config",
    default=None,
    type=click.Path(),
    help="Config file to write the extracted profile to (defaults to --config value)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def main(
    input_path,
    output_path,
    profile,
    config,
    from_image,
    extract_profile,
    save_as,
    output_config,
    verbose,
):
    """
    Paperise - Image transformation pipeline for wallpaper generation.

    Normal mode:  process INPUT_PATH and save to OUTPUT_PATH.\n
    Batch mode:   INPUT_PATH as a directory processes all images into OUTPUT_PATH directory.\n
    Replay mode:  --from-image loads the pipeline from a previously processed PNG.\n
    Extract mode: --extract-profile saves the embedded pipeline to a config file.
    """
    try:
        # ── Validation ──────────────────────────────────────────────────────
        if extract_profile:
            if not save_as:
                raise click.UsageError("--extract-profile requires --save-as NAME")
        else:
            if not input_path or not output_path:
                raise click.UsageError(
                    "INPUT_PATH and OUTPUT_PATH are required when not using --extract-profile"
                )
            if from_image and profile != "default":
                raise click.UsageError("--from-image and --profile are mutually exclusive")

        # ── Extract-profile mode ─────────────────────────────────────────────
        if extract_profile:
            if verbose:
                click.echo(f"Reading metadata from: {extract_profile}")

            meta = read_metadata(extract_profile)
            dest_config = output_config or config

            if verbose:
                click.echo(f"Profile '{meta['profile']}' (embedded) → saving as '{save_as}'")
                click.echo(f"Pipeline: {', '.join(meta['pipeline'])}")
                click.echo(f"Writing to: {dest_config}")

            overwritten = save_profile_to_config(
                save_as, meta["pipeline"], meta["params"], dest_config
            )
            if overwritten:
                click.echo(
                    f"Warning: profile '{save_as}' already existed in '{dest_config}' and was overwritten."
                )
            click.echo(
                f"✓ Profile '{save_as}' saved to '{dest_config}' "
                f"(originally '{meta['profile']}', embedded {meta['timestamp']})"
            )
            return

        # ── Load config ───────────────────────────────────────────────────────

        if verbose:
            click.echo(f"Loading configuration from: {config}")

        with open(config, "r") as f:
            config_data = yaml.safe_load(f)

        image_extensions = set(
            config_data.get("settings", {}).get(
                "image_extensions",
                [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"],
            )
        )

        # ── Resolve pipeline source ───────────────────────────────────────────
        if from_image:
            if verbose:
                click.echo(f"Loading pipeline from image metadata: {from_image}")
            meta = read_metadata(from_image)
            active_profile = meta["profile"]
            transformations = meta["pipeline"]
            parameters = meta["params"]
            if verbose:
                click.echo(f"Replaying profile: {active_profile}")
        else:
            if "profiles" not in config_data:
                raise ValueError("Configuration must contain 'profiles' section")

            if profile not in config_data["profiles"]:
                available = ", ".join(config_data["profiles"].keys())
                raise ValueError(
                    f"Profile '{profile}' not found. Available profiles: {available}"
                )

            profile_config = config_data["profiles"][profile]

            if "transformations" not in profile_config:
                raise ValueError(f"Profile '{profile}' must contain 'transformations' list")

            active_profile = profile
            transformations = profile_config["transformations"]
            parameters = profile_config.get("parameters", {})

        if verbose:
            click.echo(f"Profile: {active_profile}")
            click.echo(f"Transformations: {', '.join(transformations)}")

        # Import all transformation modules to trigger registration
        import utils  # noqa: F401

        # ── Batch (directory) mode ────────────────────────────────────────────
        input_p = Path(input_path)
        output_p = Path(output_path)

        if input_p.is_dir():
            if from_image:
                raise click.UsageError("--from-image cannot be used with a directory input")

            image_files = [
                f for f in sorted(input_p.iterdir())
                if f.is_file() and f.suffix.lower() in image_extensions
            ]

            if not image_files:
                raise ValueError(
                    f"No supported image files found in '{input_p}'. "
                    f"Supported extensions: {', '.join(sorted(image_extensions))}"
                )

            output_p.mkdir(parents=True, exist_ok=True)

            click.echo(
                f"Batch mode: {len(image_files)} image(s) in '{input_p}' → '{output_p}'"
            )

            failed = 0
            for img_file in image_files:
                out_file = output_p / img_file.name
                try:
                    _process_single_image(
                        str(img_file),
                        str(out_file),
                        transformations,
                        parameters,
                        active_profile,
                        verbose,
                    )
                except Exception as e:
                    click.echo(f"Error processing '{img_file.name}': {e}", err=True)
                    if verbose:
                        import traceback
                        traceback.print_exc()
                    failed += 1

            total = len(image_files)
            click.echo(
                f"Batch complete: {total - failed}/{total} image(s) processed successfully."
            )
            if failed:
                sys.exit(1)

        # ── Single-image mode ─────────────────────────────────────────────────
        else:
            _process_single_image(
                input_path,
                output_path,
                transformations,
                parameters,
                active_profile,
                verbose,
            )

    except click.UsageError:
        raise
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
