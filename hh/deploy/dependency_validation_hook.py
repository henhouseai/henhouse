"""
Core framework hook for module dependency validation.

This hook runs during deploy_00_pre_validate to ensure all enabled modules
have their dependencies met before deployment proceeds.
"""
from typing import Dict, Any
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


@register_module_hook('deploy_00_pre_validate', 'Validate module dependencies', priority=5)
def validate_dependencies() -> Dict[str, Any]:
    """
    Validate that all enabled modules have their dependencies met.

    This hook runs early (priority=5) to catch dependency issues before
    any deployment work begins.
    """
    trace_in()
    log("Validating module dependencies")

    from hh.gateway.registry.module_dependency_validator import validate_module_dependencies

    result = validate_module_dependencies()
    return trace_out(result)
