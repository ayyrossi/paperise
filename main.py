"""
Paperise - Wallpaper Generation Application
Image transformation pipeline with configurable profiles.
"""

import click
import cv2
import yaml
from pathlib import Path
import sys

from utils.base import TransformationRegistry, TransformationContext
from utils.io_utils import load_image, save_image, save_palette


@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option(
    '--profile',
    '-p',
    default='default',
    help='Profile name from config file'
)
@click.option(
    '--config',
    '-c',
    default='config.yaml',
    type=click.Path(exists=True),
    help='Path to configuration file'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Enable verbose output'
)
def main(input_path: str, output_path: str, profile: str, config: str, verbose: bool):
    """
    Paperise - Image transformation pipeline for wallpaper generation.

    Processes INPUT_PATH through transformation chain and saves to OUTPUT_PATH.
    Transformation chain is defined by PROFILE in configuration file.
    """
    try:
        # Load configuration
        if verbose:
            click.echo(f"Loading configuration from: {config}")

        with open(config, 'r') as f:
            config_data = yaml.safe_load(f)

        # Get profile
        if 'profiles' not in config_data:
            raise ValueError("Configuration must contain 'profiles' section")

        if profile not in config_data['profiles']:
            available = ', '.join(config_data['profiles'].keys())
            raise ValueError(
                f"Profile '{profile}' not found. Available profiles: {available}"
            )

        profile_config = config_data['profiles'][profile]

        # Validate profile structure
        if 'transformations' not in profile_config:
            raise ValueError(f"Profile '{profile}' must contain 'transformations' list")

        transformations = profile_config['transformations']
        parameters = profile_config.get('parameters', {})

        if verbose:
            click.echo(f"Profile: {profile}")
            click.echo(f"Transformations: {', '.join(transformations)}")

        # Import all transformation modules to trigger registration
        import utils

        # Load input image
        if verbose:
            click.echo(f"Loading image: {input_path}")

        image = load_image(input_path)

        if verbose:
            click.echo(f"Image size: {image.shape[1]}x{image.shape[0]}")

        # Initialize context and store original dimensions
        context = TransformationContext()
        context.metadata['original_width'] = image.shape[1]
        context.metadata['original_height'] = image.shape[0]

        # Apply transformations sequentially
        for trans_name in transformations:
            if verbose:
                click.echo(f"Applying transformation: {trans_name}")

            # Get transformation class
            try:
                trans_class = TransformationRegistry.get(trans_name)
            except KeyError as e:
                available = ', '.join(TransformationRegistry.list_transformations())
                click.echo(
                    f"Error: {e}\nAvailable transformations: {available}",
                    err=True
                )
                sys.exit(1)

            # Get parameters for this transformation
            trans_params = parameters.get(trans_name, {})

            # Create and apply transformation
            transformation = trans_class(trans_params)
            transformation.validate_params()
            image = transformation.apply(image, context)

            if verbose:
                click.echo(f"  → Output size: {image.shape[1]}x{image.shape[0]}")

        # Save output image
        if verbose:
            click.echo(f"Saving image: {output_path}")

        save_image(image, output_path)

        # Save auxiliary outputs
        output_dir = Path(output_path).parent
        output_stem = Path(output_path).stem

        # Save palette file if requested
        if context.palette and context.metadata.get('output_palette_file', False):
            palette_path = output_dir / f"{output_stem}_palette.txt"
            if verbose:
                click.echo(f"Saving palette: {palette_path}")
            save_palette(context.palette, str(palette_path))

        # Save ASCII output if present
        if context.ascii_data and context.metadata.get('ascii_output'):
            from utils.io_utils import generate_ascii_image
            ascii_path = output_dir / f"{output_stem}_ascii.png"
            font = context.metadata.get('ascii_font', 'monospace')
            font_size = context.metadata.get('ascii_font_size', 10)
            if verbose:
                click.echo(f"Saving ASCII art: {ascii_path}")
            generate_ascii_image(context.ascii_data, str(ascii_path), font, font_size)

        click.echo(f"✓ Successfully processed image: {output_path}")

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
