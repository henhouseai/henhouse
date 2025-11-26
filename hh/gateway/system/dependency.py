"""Dependency registration and checking system.

Modules can register their external dependencies using the @register_dependency decorator.
The dependency_list command then checks if all registered dependencies are available.
"""

from __future__ import annotations

from typing import Dict, Set

# Hot cache of registered dependencies: {dependency_name: set of modules that need it}
_DEPENDENCY_REGISTRY: Dict[str, Set[str]] = {}


def register_dependency(dependency_name: str):
    """Decorator to register that a module requires an external dependency.
    
    Usage:
        @register_dependency("psutil")
        def some_function():
            ...
    
    Multiple modules can register the same dependency - they'll be tracked separately.
    """
    def decorator(func):
        module_name = func.__module__
        if dependency_name not in _DEPENDENCY_REGISTRY:
            _DEPENDENCY_REGISTRY[dependency_name] = set()
        _DEPENDENCY_REGISTRY[dependency_name].add(module_name)
        return func
    return decorator


def get_registered_dependencies() -> Dict[str, Set[str]]:
    """Get all registered dependencies and the modules that need them."""
    return _DEPENDENCY_REGISTRY.copy()


def check_dependency(dependency_name: str) -> tuple[bool, str]:
    """Check if a dependency is available.
    
    Returns (is_available, error_message).
    """
    try:
        __import__(dependency_name)
        return True, ""
    except ImportError as e:
        return False, str(e)


def check_all_dependencies() -> Dict[str, Dict]:
    """Check all registered dependencies.
    
    Returns dict of {dependency_name: {"available": bool, "error": str, "modules": list}}.
    """
    results = {}
    for dep_name, modules in _DEPENDENCY_REGISTRY.items():
        available, error = check_dependency(dep_name)
        results[dep_name] = {
            "available": available,
            "error": error,
            "modules": sorted(modules),
        }
    return results


def require(dependency_name: str) -> bool:
    """Check if a dependency is available. If not, report a dependency error.
    
    Usage:
        if not require("pwd"):
            return None  # dependency error already flagged
        # ... proceed with pwd operations
    
    Returns True if dependency is available, False otherwise.
    """
    available, error = check_dependency(dependency_name)
    if not available:
        from hh.gateway.error.error_store import report_error
        report_error("dependency", f"Missing dependency: {dependency_name} - {error}")
        return False
    return True

