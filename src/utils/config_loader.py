"""
============================================================
src/utils/config_loader.py
------------------------------------------------------------
PURPOSE:
    Loads the central config.yaml file and makes settings
    accessible throughout the entire project.

HOW IT WORKS:
    - Uses PyYAML to read config.yaml
    - Returns a Python dictionary of all settings
    - Any module can import `load_config()` to get settings

USAGE:
    from src.utils.config_loader import load_config
    cfg = load_config()
    model_name = cfg['ollama']['model']
============================================================
"""

import yaml                     # PyYAML for reading YAML files
import os                       # OS path operations
from pathlib import Path        # Modern path handling
from loguru import logger       # Beautiful logging


def load_config(config_path: str = None) -> dict:
    """
    Loads configuration from config.yaml.

    Args:
        config_path: Optional custom path to config file.
                     Defaults to 'config.yaml' in project root.

    Returns:
        dict: All configuration settings as a Python dictionary.
    """
    # If no path given, find config.yaml automatically
    # It looks for config.yaml in the project root directory
    if config_path is None:
        # Walk up from this file's location to find the root
        # This file is at: src/utils/config_loader.py
        # Root is 2 levels up
        root_dir = Path(__file__).parent.parent.parent
        config_path = root_dir / "config.yaml"

    # Check if config file exists
    if not Path(config_path).exists():
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(
            f"config.yaml not found at {config_path}. "
            "Please create it from the provided template."
        )

    # Open and parse the YAML file
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)   # safe_load prevents code injection

    logger.debug(f"Config loaded from: {config_path}")
    return config


def get_project_root() -> Path:
    """
    Returns the absolute path to the project root directory.
    Useful for constructing file paths anywhere in the code.

    Returns:
        Path: Absolute path to the project root.
    """
    # This file: src/utils/config_loader.py
    # Go up 3 levels to reach project root
    return Path(__file__).parent.parent.parent
