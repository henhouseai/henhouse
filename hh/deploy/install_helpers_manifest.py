"""
Install manifest helpers.

Handles reading and writing user manifests in install config files.
"""

import os
import json
import configparser
from pathlib import Path
from typing import Dict, Any


def write_manifest_users(cfg_path: Path, manifest: Dict[str, Dict[str, Any]]) -> None:
    """
    Write user manifest to install config file.

    Creates or updates the [manifest_users] section with user records.
    """
    parser = configparser.ConfigParser()
    parser.read(cfg_path)

    if not parser.has_section("manifest_users"):
        parser.add_section("manifest_users")

    for k, v in manifest.items():
        parser.set("manifest_users", k, json.dumps(v, separators=(',', ':')))

    with open(cfg_path, 'w') as f:
        parser.write(f)

    os.chmod(cfg_path, 0o600)
