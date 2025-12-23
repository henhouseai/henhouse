"""
Extension package for user customizations.
Henhouse scans this directory for decorated modules.
This __init__.py file makes ext/ importable as a Python package, which is required
for the registry scanning to import modules from ext/ using standard Python import
mechanisms (e.g., `import ext.my_module`).
"""

