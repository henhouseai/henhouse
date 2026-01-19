"""
Maintenance Module - Background Worker Subsystem

Provides background daemon infrastructure for Henhouse projects,
including worker templates and lifecycle management.
"""

MODULE = {
    "name": "maintenance",
    "version": "1.0.0",
    "description": "Background worker subsystem - maintenance daemon and workers",
    "dependencies": ['hh_srv'],  # Requires server infrastructure for deployment
}
