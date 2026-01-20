"""
Uninstall manifest helpers for tier user removal tracking.

Updates manifest with removal timestamps.
"""

import os
import json
import datetime
import configparser
from pathlib import Path
from typing import List


def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def update_manifest_user_removal(cfg_path: Path, users: List[str]) -> None:
    """Update manifest with removal timestamps for removed users."""
    if not cfg_path.exists() or not users:
        return
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    if not parser.has_section("manifest_users"):
        return
    changed = False
    for user in users:
        if parser.has_option("manifest_users", user):
            try:
                obj = json.loads(parser.get("manifest_users", user))
                if isinstance(obj, dict):
                    obj["removed_at"] = _iso_now()
                    parser.set("manifest_users", user, json.dumps(obj, separators=(',', ':')))
                    changed = True
            except Exception:
                continue
    if changed:
        with open(cfg_path, 'w') as f:
            parser.write(f)
        os.chmod(cfg_path, 0o600)
