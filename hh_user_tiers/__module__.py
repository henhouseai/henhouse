"""
hh_user_tiers Module - Multi-Tier User System

Scope:
- System tier user creation (guest, verified, admin, root)
- User group management (project, deploy, admin groups)
- SSH key setup for tier users
- User configuration files (.{project}.cnf)
- User environment setup (sudoers, paths)
- User manifest management

This module manages the four-tier user system that provides graduated access
control from guest (public) through verified, admin, to root (panel) tiers.
"""

MODULE = {
    'name': 'hh_user_tiers',
    'description': 'Henhouse user tiers module - multi-tier user system with group management',
    'version': '1.0.0',
    'dependencies': [],  # Independent module, no dependencies
}
