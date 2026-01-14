"""
Generate TypeScript Configuration

Generates a dynamic tsconfig.json that includes TypeScript files from all active modules.
This ensures the TypeScript compiler is aware of the module architecture and can compile
module-specific TypeScript files alongside the core framework files.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, List

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
from hh.gateway.registry.registry import (
    register_action,
    register_command,
    register_parser,
)
from hh.gateway.response.json_standard import get_data, success_payload
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)

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


@register_action("generate_tsconfig")
@register_command("generate_tsconfig")
def generate_tsconfig_action() -> bool:
    """
    Generate a dynamic tsconfig.json that includes TypeScript files from all active modules.

    This action:
    1. Discovers all active (non-blacklisted) modules
    2. Checks each module for TypeScript source directories
    3. Generates a tsconfig.json with appropriate includes
    4. Handles output directory mapping for module-compiled JavaScript

    Returns:
        bool: True on success, False on error
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("action", "No gateway available")
        trace_out()
        return False

    try:
        # Get project context
        try:
            from hh.deploy.deploy_utils import detect_project_context
            project_name, project_root = detect_project_context()
        except Exception as e:
            warn(f"Error detecting project context: {e}")
            report_error("action", f"Error detecting project context: {e}")
            trace_out()
            return False

        # Get active modules
        from hh.deploy.deploy_utils import get_active_modules
        active_modules = get_active_modules()
        log(f"Found {len(active_modules)} active modules")

        # Base TypeScript config structure
        include_patterns: List[str] = [
            "hh/deploy/site/ts/**/*",
            "ext/deploy/site/ts/**/*"
        ]

        tsconfig: Dict[str, Any] = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "ES2020",
                "lib": ["ES2020", "DOM"],
                "outDir": "hh/deploy/site/js",
                "rootDir": ".",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "moduleResolution": "node"
            },
            "include": include_patterns,
            "exclude": ["node_modules"]
        }

        # Check each active module for TypeScript directories
        module_ts_dirs = []
        for module in active_modules:
            module_path = project_root / module.path

            # Check for TypeScript source directory
            ts_source_dir = module_path / "deploy" / "site" / "ts"
            if ts_source_dir.exists() and ts_source_dir.is_dir():
                # Check if directory has any TypeScript files
                ts_files = list(ts_source_dir.rglob("*.ts")) + list(ts_source_dir.rglob("*.tsx"))
                if ts_files:
                    ts_pattern = f"{module.path}/deploy/site/ts/**/*"
                    module_ts_dirs.append(ts_pattern)
                    log(f"Adding TypeScript directory for module {module.name}: {ts_pattern}")

        # Add module directories to includes
        if module_ts_dirs:
            include_patterns.extend(module_ts_dirs)
            log(f"Added {len(module_ts_dirs)} module TypeScript directories to config")

        # Write the config file
        config_path = project_root / "tsconfig.json"
        with open(config_path, 'w') as f:
            json.dump(tsconfig, f, indent=2)

        log(f"Generated tsconfig.json with {len(include_patterns)} include patterns")
        for pattern in include_patterns:
            debug(f"Include pattern: {pattern}")

        # Success response
        result = {
            "success": True,
            "message": f"Generated tsconfig.json with {len(active_modules)} active modules",
            "modules_discovered": len(active_modules),
            "ts_patterns_added": len(module_ts_dirs),
            "ts_config_generated": True,
            "ts_config_path": str(config_path)
        }

        gateway.response.set_action_response(success_payload(result))
        trace_out()
        return True

    except Exception as exc:
        warn(f"Failed to generate TypeScript config: {exc}")
        report_error("action", f"Failed to generate TypeScript config: {exc}")
        trace_out()
        return False


@register_parser("generate_tsconfig")
def generate_tsconfig_parser() -> bool:
    """
    Render generate_tsconfig action results.
    """
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

        lines = [render_header_block("generate_tsconfig_header")]

        table = TableData()
        table.add_row("generate_tsconfig_header", info="")

        # Display results
        table.add_row("modules_discovered", info=str(source_data.get("modules_discovered", 0)))
        table.add_row("ts_patterns_added", info=str(source_data.get("ts_patterns_added", 0)))
        table.add_row("ts_config_generated", info="Yes" if source_data.get("ts_config_generated", False) else "No")
        table.add_row("ts_config_path", info=source_data.get("ts_config_path", ""))

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("generate_tsconfig_header")
                .add_simple(["modules_discovered", "ts_patterns_added", "ts_config_generated", "ts_config_path"]),
                block_type="maintenance",
                table_overrides={"margin_l": 4},
            )
        )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        trace_out()
        return True

    except Exception as exc:
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False