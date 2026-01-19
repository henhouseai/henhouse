"""
hh_git Module - Git Repository Management and Framework Cleanup

Scope:
- Git directory preservation (moving to temp location before deployment)
- Git directory restoration (moving back from temp location after deployment)
- Module deployment to destination
- Framework cleanup (cleaning module deploy directories, preserving whitelisted items)
- Git directory permissions management

This module ensures the git repository is protected during deployment operations and
manages the cleanup of Python module artifacts while respecting whitelist configurations.
"""

MODULE = {
    'name': 'hh_git',
    'description': 'Henhouse Git module - repository preservation and framework cleanup',
    'version': '1.0.0',
    'dependencies': [],  # Independent module, no dependencies
}
