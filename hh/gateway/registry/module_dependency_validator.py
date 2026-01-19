"""
Module dependency validation system.

Checks that all enabled modules have their dependencies met before deployment.
"""
import importlib.util
from pathlib import Path
from typing import Dict, Any, List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, get_debug, register_debug_init
from hh.gateway.error.error_store import report_error

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


def validate_module_dependencies() -> Dict[str, Any]:
    """
    Check all enabled modules have their dependencies met.

    Returns a dict with:
    - status: "passed" or "error"
    - component: "dependencies"
    - validated_modules: count of modules checked (on success)
    - missing: dict of {module: [missing_deps]} (on error)
    """
    trace_in()

    from hh.deploy.deploy_utils import get_active_modules, detect_project_context

    # Get project root
    project_name, project_root = detect_project_context()

    # Get all active (enabled) modules
    active_modules = get_active_modules()
    enabled_module_names = {m.name for m in active_modules}

    debug(f"Validating dependencies for {len(enabled_module_names)} enabled modules")

    # Load dependencies for each module
    missing_deps: Dict[str, List[str]] = {}
    for module_info in active_modules:
        # Load the module's manifest to get dependencies
        manifest_file = project_root / module_info.path / "__module__.py"

        try:
            spec = importlib.util.spec_from_file_location("module_manifest", manifest_file)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, 'MODULE'):
                continue

            manifest_data = getattr(module, 'MODULE')
            deps = manifest_data.get('dependencies', [])

            debug(f"Module {module_info.name} declares dependencies: {deps}")

            for dep in deps:
                if dep not in enabled_module_names:
                    if module_info.name not in missing_deps:
                        missing_deps[module_info.name] = []
                    missing_deps[module_info.name].append(dep)
                    warn(f"Module {module_info.name} requires {dep} but {dep} is not enabled")

        except Exception as e:
            warn(f"Error loading manifest for {module_info.name}: {e}")

    if missing_deps:
        error_msg = "Module dependency validation failed:\n"
        for module_name, deps in missing_deps.items():
            error_msg += f"  - Module '{module_name}' requires: {', '.join(deps)}\n"
        error_msg += "\nTo fix this, either:\n"
        error_msg += "  1. Enable the required dependency modules, or\n"
        error_msg += "  2. Add the dependent modules to MODULE_BLACKLIST\n"

        report_error("dependency", error_msg)
        return trace_out({
            "status": "error",
            "component": "dependencies",
            "missing": missing_deps
        })

    log(f"Module dependency validation passed - {len(enabled_module_names)} modules validated")
    return trace_out({
        "status": "passed",
        "component": "dependencies",
        "validated_modules": len(enabled_module_names)
    })
