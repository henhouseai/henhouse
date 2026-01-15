"""Hook list tool - shows discovered module hooks and which modules provide them."""

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


@register_action("hook_list")
@register_command("hook_list")
def hook_list_action() -> bool:
    """List all discovered module hooks and which modules provide them."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False

    try:
        from hh.gateway.registry.cache import discover_all_module_hooks

        # Get hooks cache
        hooks_cache = discover_all_module_hooks()
        hooks_data_raw = hooks_cache.get('hooks', {})
        log(f"Discovered {len(hooks_data_raw)} hook names")

        # Build hook list with module information
        hooks_list: List[Dict[str, Any]] = []
        for hook_name in sorted(hooks_data_raw.keys()):
            hook_entries = hooks_data_raw[hook_name]

            # Get modules that provide this hook (sorted alphabetically)
            modules = sorted([entry.get('module_name', 'unknown') for entry in hook_entries])

            hook_info: Dict[str, Any] = {
                "hook_name": hook_name,
                "modules": modules,
                "module_count": len(modules),
            }
            hooks_list.append(hook_info)
            debug(f"Hook {hook_name}: {len(modules)} modules")

        payload = {
            "total_hooks": len(hooks_list),
            "hooks": hooks_list,
        }

        gateway.response.set_action_response(success_payload(payload))
        log(f"Hook list created: {len(hooks_list)} hooks")
        trace_out()
        return True

    except Exception as exc:
        warn(f"Failed to list hooks: {exc}")
        report_error("action", f"Failed to list hooks: {exc}")
        trace_out()
        return False


@register_parser("hook_list")
def hook_list_parser() -> bool:
    """Render hook list with modules."""
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

        total_hooks = source_data.get("total_hooks", 0)
        hooks = source_data.get("hooks", [])

        lines = [render_header_block("l_hook_list_header")]

        if total_hooks == 0:
            lines.append("No module hooks registered.")
        else:
            # Build hooks table
            table = TableData()

            # Header row
            table.add_row(
                "hook_list_header",
                hook_name="Hook Name",
                modules="Modules",
                count="Count",
            )

            for hook_info in hooks:
                hook_name = hook_info.get("hook_name", "unknown")
                modules = hook_info.get("modules", [])
                module_count = hook_info.get("module_count", 0)

                # Format modules as comma-separated list
                modules_str = ", ".join(modules) if modules else "-"

                table.add_row(
                    "hook_row",
                    hook_name=safe_str(hook_name),
                    modules=safe_str(modules_str),
                    count=str(module_count),
                )

            # Field config
            field_config = (FieldConfig()
                .add_header("hook_list_header")
                .add_simple(["hook_row"])
                .add_simple(["hook_name", "modules", "count"]))

            lines.append(
                render_block(
                    table,
                    field_config,
                    block_type="rows",
                    table_overrides={"margin_l": 4},
                )
            )

            # Summary
            summary = TableData()
            summary.add_row("hook_summary_header", info="")
            summary.add_row("total_hooks", info=str(total_hooks))

            lines.append(
                render_block(
                    summary,
                    FieldConfig()
                    .add_header("hook_summary_header")
                    .add_simple(["total_hooks"]),
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
