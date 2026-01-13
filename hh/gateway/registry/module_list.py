"""Module list tool - shows discovered modules and their blacklist status."""

from __future__ import annotations

from typing import List, Dict, Any

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
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)
from hh.render.config.config import break_section, safe_str

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message=None: None


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_action("module_list")
@register_command("module_list")
def module_list_action() -> bool:
    """List all discovered modules and their status (enabled/blacklisted)."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False

    try:
        from hh.deploy.deploy_utils import get_active_modules, get_all_modules

        # Get all discovered modules (before blacklist filtering)
        all_modules = get_all_modules()
        log(f"Discovered {len(all_modules)} total modules")

        # Get active modules (after blacklist filtering)
        active_modules = get_active_modules()
        active_module_names = {m.name for m in active_modules}
        log(f"Found {len(active_modules)} active modules")

        # Build module list with status
        modules_data: List[Dict[str, Any]] = []
        for module in sorted(all_modules, key=lambda m: m.name):
            is_enabled = module.name in active_module_names
            module_info: Dict[str, Any] = {
                "name": module.name,
                "path": module.path,
                "description": module.description or "",
                "version": module.version or "",
                "is_enabled": is_enabled,
                "status": "enabled" if is_enabled else "blacklisted",
            }
            modules_data.append(module_info)
            debug(f"Module {module.name}: {module_info['status']}")

        payload = {
            "total_modules": len(all_modules),
            "enabled_modules": len(active_modules),
            "blacklisted_modules": len(all_modules) - len(active_modules),
            "modules": modules_data,
        }

        gateway.response.set_action_response(success_payload(payload))
        log(
            f"Module list created: {len(active_modules)}/{len(all_modules)} enabled, "
            f"{len(all_modules) - len(active_modules)} blacklisted"
        )
        trace_out()
        return True

    except Exception as exc:
        warn(f"Failed to list modules: {exc}")
        report_error("action", f"Failed to list modules: {exc}")
        trace_out()
        return False


@register_parser("module_list")
def module_list_parser() -> bool:
    """Render module list with status."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False

    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data if json_data is not None else {})

        total_modules = source_data.get("total_modules", 0)
        enabled_modules = source_data.get("enabled_modules", 0)
        blacklisted_modules = source_data.get("blacklisted_modules", 0)
        modules = source_data.get("modules", [])

        lines = [render_header_block("l_module_list_header")]

        # Check if any module has name != path (to decide if we need path column)
        show_path = any(m.get("name", "") != m.get("path", "") for m in modules)

        # Build module table
        table = TableData()

        # Header row - conditionally include path
        if show_path:
            table.add_row(
                "module_list_header",
                name="Module",
                path="Path",
                description="Description",
            )
        else:
            table.add_row(
                "module_list_header",
                name="Module",
                description="Description",
            )

        for module_info in modules:
            name = module_info.get("name", "unknown")
            status = module_info.get("status", "unknown")
            path = module_info.get("path", "")
            description = module_info.get("description", "")
            version = module_info.get("version", "")

            # Add version to description if present
            desc_with_version = f"{description} (v{version})" if version else description

            if status == "enabled":
                if show_path:
                    table.add_row(
                        "module_enabled",
                        name=safe_str(name),
                        path=safe_str(path),
                        description=safe_str(desc_with_version),
                    )
                else:
                    table.add_row(
                        "module_enabled",
                        name=safe_str(name),
                        description=safe_str(desc_with_version),
                    )
            else:
                if show_path:
                    table.add_row(
                        "module_blacklisted",
                        name=safe_str(name),
                        path=safe_str(path),
                        description=safe_str(desc_with_version),
                    )
                else:
                    table.add_row(
                        "module_blacklisted",
                        name=safe_str(name),
                        description=safe_str(desc_with_version),
                    )

        # Field config - conditionally include path
        field_config = (FieldConfig()
            .add_header("module_list_header")
            .add_simple_color("module_enabled", "green")
            .add_simple_color("module_blacklisted", "red"))

        if show_path:
            field_config.add_simple(["name", "path", "description"])
        else:
            field_config.add_simple(["name", "description"])

        lines.append(
            render_block(
                table,
                field_config,
                block_type="rows",
                table_overrides={"margin_l": 4},
            )
        )

        # Summary table (vertical layout like maintenance-jobs-status)
        summary = TableData()
        summary.add_row("module_summary_header", info="")
        summary.add_row("total_modules", info=str(total_modules))
        summary.add_row("enabled_modules", info=str(enabled_modules))
        summary.add_row("blacklisted_modules", info=str(blacklisted_modules))

        lines.append(
            render_block(
                summary,
                FieldConfig()
                .add_header("module_summary_header")
                .add_simple(["total_modules", "enabled_modules"])
                .add_simple_color("blacklisted_modules", "red" if blacklisted_modules > 0 else "green"),
                block_type="maintenance",
                table_overrides={"margin_l": 4},
            )
        )

        break_section(lines)
        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} sections")
        trace_out()
        return True

    except Exception as exc:
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False
