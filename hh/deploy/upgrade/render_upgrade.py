from __future__ import annotations
from typing import Dict, List, Union, Any
from hh.gateway.registry.registry import register_parser
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data

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


def render_upgrade_section(source_data: Dict[str, Union[str, int, bool, List[str]]], lines: List[str]) -> None:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_upgrade_section")
        trace_out()
        return
    
    block = 'upgrade'
    if not gateway.is_no(block):
        upgrade_data = TableData()
        target = source_data.get('target', 'Unknown')
        backup_name = source_data.get('backup_name', 'Unknown')
        context_backup_name = source_data.get('context_backup_name')
        restored_files_raw: Any = source_data.get('restored_files', [])
        restored_files: List[str] = restored_files_raw if isinstance(restored_files_raw, list) else []
        restored_count = source_data.get('restored_count', 0)
        
        log(f"Rendering upgrade section for: {target}")
        debug(f"Source data keys: {list(source_data.keys())}")
        debug(f"Restored files: {restored_files}, type: {type(restored_files)}")
        
        # Target header
        upgrade_data.add_row(
            'target_header',
            value=safe_str(target)
        )
        
        # Backup name
        upgrade_data.add_row(
            'backup_created',
            value=safe_str(backup_name)
        )
        
        # Context backup name (if exists)
        if context_backup_name:
            upgrade_data.add_row(
                'context_backup_created',
                value=safe_str(context_backup_name)
            )
        
        # Restored files
        if restored_files:
            for file_path in restored_files:
                upgrade_data.add_row(
                    'file_restored',
                    value=safe_str(file_path)
                )
        else:
            upgrade_data.add_row(
                'file_restored',
                value='None'
            )
        
        # Reminder messages
        upgrade_data.add_row(
            'backup_reminder',
            value='Delete backup directory when satisfied with upgrade'
        )
        upgrade_data.add_row(
            'test_reminder',
            value='Test thoroughly - preserved files may be incompatible with new version'
        )
        
        debug(f"Final upgrade_data: {upgrade_data.num_rows()} items")
        
        # Build simple fields list (conditionally include context_backup_created)
        simple_fields = ['backup_created']
        if context_backup_name:
            simple_fields.append('context_backup_created')
        simple_fields.extend([
            'file_restored',
            'backup_reminder',
            'test_reminder',
        ])
        
        lines.append(render_block(
            upgrade_data,
            FieldConfig()
                .add_header('target_header')
                .add_simple(simple_fields),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


@register_parser('upgrade')
def upgrade() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    
    json_data = gateway.response.get_action_response()
    lines = []
    lines.append(render_header_block('l_upgrade_header'))
    source_data = get_data(json_data) if json_data else {}
    log(f"Processing upgrade data successfully")
    
    render_upgrade_section(source_data, lines)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True

