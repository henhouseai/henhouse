#!/usr/bin/env python3
"""
Main maintenance daemon worker.

This worker handles:
- Page cache refresh
- Orphan checks
- Pending jobs from maintenance_jobs table
- Other maintenance tasks registered for the "maintenance" daemon
"""
from maintenance.deploy.apps.base_worker import main

if __name__ == "__main__":
    raise SystemExit(main())
