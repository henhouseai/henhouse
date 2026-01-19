"""
Module dependency validation system.

Checks that all enabled modules have their dependencies met before deployment.
"""
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

    from hh.gateway.registry.modules import get_discovered_modules

    discovered = get_discovered_modules()
    enabled_modules = {name for name, info in discovered.items()
                      if not info.get('blacklisted', False)}

    debug(f"Validating dependencies for {len(enabled_modules)} enabled modules")

    missing_deps = {}
    for module_name in enabled_modules:
        module_info = discovered[module_name]
        deps = module_info.get('dependencies', [])

        debug(f"Module {module_name} declares dependencies: {deps}")

        for dep in deps:
            if dep not in enabled_modules:
                if module_name not in missing_deps:
                    missing_deps[module_name] = []
                missing_deps[module_name].append(dep)
                warn(f"Module {module_name} requires {dep} but {dep} is not enabled")

    if missing_deps:
        error_msg = "Module dependency validation failed:\n"
        for module, deps in missing_deps.items():
            error_msg += f"  - Module '{module}' requires: {', '.join(deps)}\n"
        error_msg += "\nTo fix this, either:\n"
        error_msg += "  1. Enable the required dependency modules, or\n"
        error_msg += "  2. Add the dependent modules to MODULE_BLACKLIST\n"

        report_error("dependency", error_msg)
        return trace_out({
            "status": "error",
            "component": "dependencies",
            "missing": missing_deps
        })

    log(f"Module dependency validation passed - {len(enabled_modules)} modules validated")
    return trace_out({
        "status": "passed",
        "component": "dependencies",
        "validated_modules": len(enabled_modules)
    })
