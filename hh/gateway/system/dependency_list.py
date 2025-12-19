"""Dependency list command - shows status of external dependencies."""

from __future__ import annotations

from hh.gateway.error.error_store import report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)
from hh.gateway.system.dependency import (
    check_all_dependencies,
    get_registered_dependencies,
)
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)

trace_in = lambda message=None: None
trace_out = lambda message=None: None
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


_DEPENDENCY_DECORATOR_NAME = "register_dependency"


def _scan_and_import_dependencies():
    """Scan for dependency decorators and import those modules."""
    from pathlib import Path
    import importlib
    
    decorator_pattern = "@" + _DEPENDENCY_DECORATOR_NAME
    
    try:
        import hh
        hh_path = Path(hh.__file__).parent
        
        for py_file in hh_path.rglob("*.py"):
            if py_file.name.startswith("cache_"):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if decorator_pattern in content:
                        rel_path = py_file.relative_to(hh_path)
                        module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
                        module_path = "hh." + ".".join(module_parts)
                        try:
                            importlib.import_module(module_path)
                            log(f"Imported {module_path} for dependency registration")
                        except Exception as e:
                            debug(f"Failed to import {module_path}: {e}")
            except Exception as e:
                debug(f"Error reading {py_file}: {e}")
    except Exception as e:
        warn(f"Error scanning for dependencies: {e}")


@register_action("dependency_list")
@register_command("dependency_list")
def dependency_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    try:
        # Scan and import all modules with @register_dependency
        _scan_and_import_dependencies()
        
        # Check all registered dependencies
        results = check_all_dependencies()
        
        # Build response data
        dependencies = []
        all_available = True
        for dep_name, info in sorted(results.items()):
            dep_data = {
                "name": dep_name,
                "available": info["available"],
                "modules": info["modules"],
            }
            if not info["available"]:
                dep_data["error"] = info["error"]
                all_available = False
            dependencies.append(dep_data)
        
        data = {
            "type": "dependency_list",
            "count": len(dependencies),
            "all_available": all_available,
            "dependencies": dependencies,
        }
        
        log(f"Checked {len(dependencies)} dependencies, all_available={all_available}")
        gateway.response.set_action_response(success_payload(data))
        trace_out()
        return True
    except Exception as e:  # noqa: BLE001
        warn(f"Error checking dependencies: {e}")
        report_error("action", f"Error checking dependencies: {e}")
        trace_out()
        return False


@register_parser("dependency_list")
def dependency_list_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway or response available")
        trace_out()
        return False

    try:
        action_resp = gateway.response.get_action_response()
        source_data = get_data(action_resp) if action_resp is not None else {}
        dependencies = source_data.get("dependencies", [])
        all_available = source_data.get("all_available", True)
        count = source_data.get("count", 0)
        
        lines = [render_header_block("l_dependency_list")]
        
        if count == 0:
            # No dependencies registered
            table = TableData()
            table.add_row("no_dependencies", info="No external dependencies registered")
            lines.append(
                render_block(
                    table,
                    FieldConfig().add_simple(["no_dependencies"]),
                    block_type="info",
                    table_overrides={"margin_l": 4},
                )
            )
        else:
            table = TableData()
            table.add_row(
                "dependency_header",
                info=f"{count} dependencies",
                col_b="required by",
            )
            
            for dep in dependencies:
                name = dep["name"]
                available = dep["available"]
                modules = dep.get("modules", [])
                
                # Format modules list - always show full list
                modules_str = ", ".join(m.split(".")[-1] for m in modules)
                
                if available:
                    table.add_row(
                        "dependency_available",
                        info=name,
                        col_b=modules_str,
                    )
                else:
                    table.add_row(
                        "dependency_missing",
                        info=name,
                        col_b=modules_str,
                    )
            
            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_header("dependency_header")
                    .add_simple_color("dependency_available", "green")
                    .add_simple_color("dependency_missing", "red"),
                    block_type="list",
                    table_overrides={"margin_l": 4},
                )
            )
        
        gateway.response.add_output(finalize_output(lines))
        trace_out()
        return True
    except Exception as e:  # noqa: BLE001
        warn(f"Parser error: {e}")
        report_error("backend", f"Parser error: {e}")
        trace_out()
        return False

