"""
self_doc Module - Self-Documentation System

Scope:
- Context folder and file deployment to deployment directory
- Documentation structure management

This module deploys context documentation files (patterns.md, overview.md, etc.)
to the deployment directory, making documentation available on the deployed server.
"""

MODULE = {
    'name': 'self_doc',
    'description': 'Self-documentation system for Henhouse - context file deployment',
    'version': '1.0.0',
    'dependencies': ['hh_srv'],  # Requires server infrastructure for context deployment
}
