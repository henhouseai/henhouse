"""
Where maintenance workers live when running from a working copy (not deployed to /srv).

Deployed workers are copied to /srv/<project>/<project>_maintenance[_<daemon>].py by the
maintenance deploy hook; these helpers cover the undeployed (development) case.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict


def dev_main_worker(project_root: Path) -> Path:
    """Main maintenance worker script in a working copy."""
    return project_root / "maintenance" / "deploy" / "apps" / "maintenance_worker.py"


DEV_MAIN_WORKER_PROCESS = "maintenance_worker.py"


def dev_module_workers(project_root: Path) -> Dict[str, Path]:
    """
    Extra daemon workers shipped by active modules: <module>/deploy/maintenance/<daemon>_worker.py.

    Returns {daemon_name: worker_path}.  Mirrors what the maintenance deploy hook copies to /srv.
    """
    from hh.deploy.deploy_utils import get_active_modules

    workers: Dict[str, Path] = {}
    for module in get_active_modules():
        maint_dir = project_root / module.path / "deploy" / "maintenance"
        if maint_dir.is_dir():
            for worker_file in sorted(maint_dir.glob("*_worker.py")):
                workers[worker_file.stem.replace("_worker", "")] = worker_file
    return workers
