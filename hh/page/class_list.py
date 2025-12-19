from __future__ import annotations
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.page.page_class_registry import discover_page_classes, _page_class_registry
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section
from hh.gateway.response.json_standard import get_data
from typing import Mapping, cast, Any
from hh.render.config.config import safe_str

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


@register_action("class_list")
@register_command("class_list")
def class_list() -> bool:
    """Force rebuild page class cache and report all classes with their status."""
    trace_in()
    gateway = get_gateway()

    try:
        # Force a complete rebuild of the page class cache
        log("Forcing page class cache rebuild...")
        class_data = discover_page_classes(force_regenerate=True)
        
        # Collect results
        classes = []
        total_classes = 0
        loaded_classes = 0
        failed_classes = 0
        
        for class_name, class_info in sorted(class_data.items()):
            total_classes += 1
            
            # Map the registry's load_status to our expected status
            load_status = class_info.get("load_status", "unknown")
            status = "loaded" if load_status == "success" else "failed"
            
            class_entry = {
                "name": class_name,
                "status": status,
                "module": class_info.get("module", "unknown"),
            }
            
            if status == "loaded":
                loaded_classes += 1
                class_entry["description"] = class_info.get("description", "")
            else:
                failed_classes += 1
                class_entry["error"] = class_info.get("load_error", "Unknown error")
            
            classes.append(class_entry)
        
        # Build response data
        data = {
            "type": "class_list",
            "total_classes": total_classes,
            "loaded_classes": loaded_classes,
            "failed_classes": failed_classes,
            "has_errors": failed_classes > 0,
            "classes": classes,
        }
        
        log(f"Page class rebuild complete: {loaded_classes}/{total_classes} loaded, {failed_classes} failed")
        gateway.response.set_action_response(success_payload(data))
        trace_out()
        return True
        
    except Exception as e:
        warn(f"Error rebuilding page class cache: {e}")
        report_error("action", f"Error rebuilding page class cache: {e}")
        trace_out()
        return False


@register_parser("class_list")
def class_list_parser() -> bool:
    """Render page class list with status and errors."""
    trace_in()
    gateway = get_gateway()
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        action_response = gateway.response.get_action_response()
        if action_response is None:
            warn("Action response is None")
            report_error("backend", "Action response is None")
            trace_out()
            return False
        source_data = get_data(cast(Mapping[str, Any], action_response))
        total_classes = source_data.get("total_classes", 0)
        loaded_classes = source_data.get("loaded_classes", 0)
        failed_classes = source_data.get("failed_classes", 0)
        has_errors = source_data.get("has_errors", False)
        classes = source_data.get("classes", [])

        lines = [render_header_block("l_class_list_header")]

        # Class details table
        if classes:
            class_table = TableData()
            
            # Conditionally include error column only if there are errors
            if has_errors:
                class_table.add_row("class_details_header", class_name="Class", status="Status", module="Module", error="Error/Description")
            else:
                class_table.add_row("class_details_header", class_name="Class", status="Status", module="Module")
            
            for class_info in classes:
                class_name = class_info.get("name", "unknown")
                status = class_info.get("status", "unknown")
                module = class_info.get("module", "unknown")
                
                if status == "loaded":
                    description = class_info.get("description", "")
                    if has_errors:
                        class_table.add_row(
                            "loaded_class",
                            class_name=safe_str(class_name),
                            status="✅ Loaded",
                            module=safe_str(module),
                            error=safe_str(description)
                        )
                    else:
                        class_table.add_row(
                            "loaded_class",
                            class_name=safe_str(class_name),
                            status="✅ Loaded",
                            module=safe_str(module)
                        )
                else:
                    error = class_info.get("error", "Unknown error")
                    if has_errors:
                        class_table.add_row(
                            "failed_class",
                            class_name=safe_str(class_name),
                            status="❌ Failed",
                            module=safe_str(module),
                            error=safe_str(error)
                        )
                    else:
                        # This shouldn't happen since has_errors would be True, but for completeness
                        class_table.add_row(
                            "failed_class",
                            class_name=safe_str(class_name),
                            status="❌ Failed",
                            module=safe_str(module)
                        )

            # Conditionally include error column in field config
            field_config = (FieldConfig()
                .add_header('header')
                .add_simple_color('loaded_class', 'green')
                .add_simple_color('failed_class', 'red'))
            
            if has_errors:
                field_config.add_simple(['class_name', 'status', 'module', 'error'])
            else:
                field_config.add_simple(['class_name', 'status', 'module'])

            lines.append(
                render_block(
                    class_table,
                    field_config,
                    table_overrides={'margin_l': 4},
                    block_type='rows'
                )
            )

        break_section(lines)
        result = finalize_output(lines)
        gateway.response.add_output(result)
        log(f"Class list parser output length: {len(result)}")
        trace_out()
        return True
        
    except Exception as e:
        warn("Parser execution raised an exception.")
        report_error("backend", f"Parser execution raised an exception: {e}")
        trace_out()
        return False
