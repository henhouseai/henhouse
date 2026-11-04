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
    """List all discovered module hooks with individual module registrations."""
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

        # Build expanded hook list - one entry per module registration
        hook_registrations: List[Dict[str, Any]] = []
        for hook_name in sorted(hooks_data_raw.keys()):
            hook_entries = hooks_data_raw[hook_name]

            # Extract prefix from hook_name (everything before underscore followed by digit)
            prefix = hook_name
            for i in range(len(hook_name) - 1):
                if hook_name[i] == '_' and hook_name[i + 1].isdigit():
                    prefix = hook_name[:i]
                    break

            # Create one entry per module registration
            for entry in hook_entries:
                module_name = entry.get('module_name', 'unknown')
                description = entry.get('description', '')

                registration: Dict[str, Any] = {
                    "hook_name": hook_name,
                    "module_name": module_name,
                    "description": description,
                    "prefix": prefix,
                }
                hook_registrations.append(registration)
                debug(f"Hook {hook_name} registered by {module_name}")

        payload = {
            "total_registrations": len(hook_registrations),
            "registrations": hook_registrations,
        }

        gateway.response.set_action_response(success_payload(payload))
        log(f"Hook list created: {len(hook_registrations)} total registrations")
        trace_out()
        return True

    except Exception as exc:
        warn(f"Failed to list hooks: {exc}")
        report_error("action", f"Failed to list hooks: {exc}")
        trace_out()
        return False


@register_parser("hook_list")
def hook_list_parser() -> bool:
    """Render hook list with separate tables per prefix."""
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

        total_registrations = source_data.get("total_registrations", 0)
        registrations = source_data.get("registrations", [])

        lines = [render_header_block("l_hook_list_header")]

        if total_registrations == 0:
            lines.append("No module hooks registered.")
        else:
            # Group registrations by prefix
            registrations_by_prefix: Dict[str, List[Dict[str, Any]]] = {}
            for reg in registrations:
                prefix = reg.get("prefix", "unknown")
                if prefix not in registrations_by_prefix:
                    registrations_by_prefix[prefix] = []
                registrations_by_prefix[prefix].append(reg)

            log(f"Grouped registrations into {len(registrations_by_prefix)} prefixes")

            # Create separate table for each prefix
            for prefix in sorted(registrations_by_prefix.keys()):
                prefix_registrations = registrations_by_prefix[prefix]
                log(f"Rendering table for prefix '{prefix}' with {len(prefix_registrations)} registrations")

                table = TableData()

                # Header row with label override to show prefix
                table.add_row(
                    "hook_list_header",
                    label=prefix,
                    hook_name="Hook Name",
                    module="Module",
                    description="Description",
                )

                # Group by hook_name to calculate section breaks
                hooks_in_prefix: Dict[str, List[Dict[str, Any]]] = {}
                for reg in prefix_registrations:
                    hook_name = reg.get("hook_name", "unknown")
                    if hook_name not in hooks_in_prefix:
                        hooks_in_prefix[hook_name] = []
                    hooks_in_prefix[hook_name].append(reg)

                # Build table rows with section breaks between hook names
                separator_rows = []
                current_row = 1  # Start after header
                sorted_hook_names = sorted(hooks_in_prefix.keys())

                for hook_idx, hook_name in enumerate(sorted_hook_names):
                    hook_regs = sorted(hooks_in_prefix[hook_name], key=lambda r: r.get("module_name", ""))

                    for reg_idx, reg in enumerate(hook_regs):
                        module_name = reg.get("module_name", "unknown")
                        description = reg.get("description", "")

                        # Only show hook_name on first row of each group
                        hook_name_display = safe_str(hook_name) if reg_idx == 0 else ""

                        table.add_row(
                            "hook_row",
                            hook_name=hook_name_display,
                            module=safe_str(module_name),
                            description=safe_str(description),
                        )
                        current_row += 1

                    # Add section break after each hook name group (except last)
                    if hook_idx < len(sorted_hook_names) - 1:
                        separator_rows.append(current_row - 1)

                # Field config
                field_config = (FieldConfig()
                    .add_header("hook_list_header")
                    .add_simple(["hook_row"]))

                # Table overrides with section breaks
                table_overrides: Dict[str, Any] = {"margin_l": 4}
                if separator_rows:
                    table_overrides["separator_after_rows"] = separator_rows

                lines.append(
                    render_block(
                        table,
                        field_config,
                        block_type="rows",
                        table_overrides=table_overrides,
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
