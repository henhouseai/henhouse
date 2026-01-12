"""
Module Discovery - Manifest Loader Utility

Minimal utility for loading module manifests during smoke testing.
Full discovery system will be implemented in Ask 1264.
"""

import os
import importlib.util
from typing import Optional


def load_manifest(folder_path: str) -> Optional[dict]:
    """
    Load MODULE dict from __module__.py in folder.

    Args:
        folder_path: Path to module folder containing __module__.py

    Returns:
        MODULE dict if found and valid, None otherwise

    Example:
        >>> manifest = load_manifest('self-doc')
        >>> print(manifest['name'])
        'self-doc'
    """
    manifest_file = os.path.join(folder_path, '__module__.py')

    if not os.path.exists(manifest_file):
        return None

    try:
        # Load the __module__.py file dynamically
        spec = importlib.util.spec_from_file_location('__module__', manifest_file)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Extract MODULE dict
        if hasattr(module, 'MODULE'):
            manifest = module.MODULE

            # Validate according to spec from task 1301
            if not isinstance(manifest, dict):
                return None
            if 'name' not in manifest or not manifest['name']:
                return None

            return manifest

        return None

    except Exception:
        # Fail gracefully on any import/parsing errors
        return None
