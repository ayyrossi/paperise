"""
PNG metadata helpers for pipeline embedding and replay.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from PIL import Image, PngImagePlugin


def build_pnginfo(profile_name: str, pipeline: list, params: dict, palette: list = None) -> PngImagePlugin.PngInfo:
    """
    Build a PngInfo object with paperise pipeline metadata as text chunks.

    Args:
        profile_name: Name of the profile used
        pipeline: Ordered list of transformation names
        params: Dictionary mapping transformation names to parameter dicts
        palette: Optional list of BGR color tuples from quantization (stored as RGB hex strings)

    Returns:
        PngInfo object ready to pass to image.save(path, pnginfo=pnginfo)
    """
    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add_text("paperise:profile", profile_name)
    pnginfo.add_text("paperise:pipeline", json.dumps(pipeline))
    pnginfo.add_text("paperise:params", json.dumps(params))
    pnginfo.add_text("paperise:timestamp", datetime.now(timezone.utc).isoformat())
    if palette:
        hex_palette = [f"#{r:02x}{g:02x}{b:02x}" for b, g, r in palette]
        pnginfo.add_text("paperise:palette", json.dumps(hex_palette))
    return pnginfo


def read_metadata(image_path: str) -> dict:
    """
    Read paperise pipeline metadata from a PNG file's text chunks.

    Args:
        image_path: Path to the PNG file

    Returns:
        Dict with keys: profile (str), pipeline (list), params (dict), timestamp (str)

    Raises:
        ValueError: If the image contains no paperise metadata
    """
    img = Image.open(image_path)
    text = getattr(img, "text", {})

    paperise_keys = {k: v for k, v in text.items() if k.startswith("paperise:")}
    if not paperise_keys:
        raise ValueError(
            f"No paperise metadata found in '{image_path}'. "
            "Only PNG images processed by paperise contain embedded pipeline data."
        )

    return {
        "profile": paperise_keys.get("paperise:profile", ""),
        "pipeline": json.loads(paperise_keys.get("paperise:pipeline", "[]")),
        "params": json.loads(paperise_keys.get("paperise:params", "{}")),
        "timestamp": paperise_keys.get("paperise:timestamp", ""),
    }


def save_profile_to_config(
    profile_name: str, pipeline: list, params: dict, config_path: str
) -> bool:
    """
    Insert or overwrite a profile in a YAML config file.

    Args:
        profile_name: Name to store the profile under
        pipeline: Ordered list of transformation names
        params: Dictionary mapping transformation names to parameter dicts
        config_path: Path to the target YAML config file

    Returns:
        True if an existing profile was overwritten, False if it was newly created
    """
    path = Path(config_path)
    if path.exists():
        with open(path, "r") as f:
            config_data = yaml.safe_load(f) or {}
    else:
        config_data = {}

    if "profiles" not in config_data:
        config_data["profiles"] = {}

    overwritten = profile_name in config_data["profiles"]

    config_data["profiles"][profile_name] = {
        "transformations": pipeline,
        "parameters": params,
    }

    with open(path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    return overwritten
