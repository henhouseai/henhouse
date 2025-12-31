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
        dry_run = source_data.get('dry_run', False)
        
        # Get categorized HH diffs
        hh_diffs_lost_raw: Any = source_data.get('hh_diffs_lost', [])
        hh_diffs_lost: List[str] = hh_diffs_lost_raw if isinstance(hh_diffs_lost_raw, list) else []
        hh_diffs_restored_raw: Any = source_data.get('hh_diffs_restored', [])
        hh_diffs_restored: List[str] = hh_diffs_restored_raw if isinstance(hh_diffs_restored_raw, list) else []
        hh_diffs_created_raw: Any = source_data.get('hh_diffs_created', [])
        hh_diffs_created: List[str] = hh_diffs_created_raw if isinstance(hh_diffs_created_raw, list) else []
        hh_diffs_updated_raw: Any = source_data.get('hh_diffs_updated', [])
        hh_diffs_updated: List[str] = hh_diffs_updated_raw if isinstance(hh_diffs_updated_raw, list) else []
        hh_diffs_preserved_raw: Any = source_data.get('hh_diffs_preserved', [])
        hh_diffs_preserved: List[str] = hh_diffs_preserved_raw if isinstance(hh_diffs_preserved_raw, list) else []
        hh_total_raw: Any = source_data.get('hh_diff_count_total', 0)
        hh_total: int = hh_total_raw if isinstance(hh_total_raw, int) else 0
        
        # Get categorized context diffs
        context_diffs_lost_raw: Any = source_data.get('context_diffs_lost', [])
        context_diffs_lost: List[str] = context_diffs_lost_raw if isinstance(context_diffs_lost_raw, list) else []
        context_diffs_restored_raw: Any = source_data.get('context_diffs_restored', [])
        context_diffs_restored: List[str] = context_diffs_restored_raw if isinstance(context_diffs_restored_raw, list) else []
        context_diffs_created_raw: Any = source_data.get('context_diffs_created', [])
        context_diffs_created: List[str] = context_diffs_created_raw if isinstance(context_diffs_created_raw, list) else []
        context_diffs_updated_raw: Any = source_data.get('context_diffs_updated', [])
        context_diffs_updated: List[str] = context_diffs_updated_raw if isinstance(context_diffs_updated_raw, list) else []
        context_diffs_preserved_raw: Any = source_data.get('context_diffs_preserved', [])
        context_diffs_preserved: List[str] = context_diffs_preserved_raw if isinstance(context_diffs_preserved_raw, list) else []
        context_total_raw: Any = source_data.get('context_diff_count_total', 0)
        context_total: int = context_total_raw if isinstance(context_total_raw, int) else 0
        has_context_diffs = source_data.get('context_diffs_lost') is not None
        
        log(f"Rendering upgrade section for: {target}")
        debug(f"Source data keys: {list(source_data.keys())}")
        debug(f"Dry run: {dry_run}, HH total: {hh_total}, Context total: {context_total}")
        
        # Target header
        upgrade_data.add_row(
            'target_header',
            value=safe_str(target)
        )
        
        # Status (dry run or upgraded)
        if dry_run:
            upgrade_data.add_row(
                'status',
                value='DRY RUN - No files modified'
            )
        else:
            upgrade_data.add_row(
                'status',
                value='Upgrade completed'
            )
        
        # Backup name (only show if not dry run)
        if not dry_run:
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
        
        # File differences - HH folder (categorized)
        # Each category is rendered as a separate section
        if hh_total > 0:
            # Files that will be lost (red)
            if hh_diffs_lost:
                count = len(hh_diffs_lost)
                category_data = TableData()
                category_data.add_row(
                    'status',
                    value=f'Will be lost ({count} files)'
                )
                for file_path in sorted(hh_diffs_lost):
                    category_data.add_row(
                        'hh_diff_lost',
                        value=safe_str(file_path)
                    )
                lines.append(render_block(
                    category_data,
                    FieldConfig().add_simple(['status', 'hh_diff_lost']).add_simple_color('hh_diff_lost', 'red'),
                    table_overrides={'margin_l': 4},
                    block_type=block
                ))
                break_section(lines)
            
            # Files that will be restored (green)
            if hh_diffs_restored:
                count = len(hh_diffs_restored)
                category_data = TableData()
                category_data.add_row(
                    'status',
                    value=f'Will be restored ({count} files)'
                )
                for file_path in sorted(hh_diffs_restored):
                    category_data.add_row(
                        'hh_diff_restored',
                        value=safe_str(file_path)
                    )
                lines.append(render_block(
                    category_data,
                    FieldConfig().add_simple(['status', 'hh_diff_restored']).add_simple_color('hh_diff_restored', 'green'),
                    table_overrides={'margin_l': 4},
                    block_type=block
                ))
                break_section(lines)
            
            # Files that will be created
            if hh_diffs_created:
                count = len(hh_diffs_created)
                category_data = TableData()
                category_data.add_row(
                    'status',
                    value=f'Will be created ({count} files)'
                )
                for file_path in sorted(hh_diffs_created):
                    category_data.add_row(
                        'hh_diff_created',
                        value=safe_str(file_path)
                    )
                lines.append(render_block(
                    category_data,
                    FieldConfig().add_simple(['status', 'hh_diff_created']),
                    table_overrides={'margin_l': 4},
                    block_type=block
                ))
                break_section(lines)
            
            # Files that will be updated
            if hh_diffs_updated:
                count = len(hh_diffs_updated)
                category_data = TableData()
                category_data.add_row(
                    'status',
                    value=f'Will be updated ({count} files)'
                )
                for file_path in sorted(hh_diffs_updated):
                    category_data.add_row(
                        'hh_diff_updated',
                        value=safe_str(file_path)
                    )
                lines.append(render_block(
                    category_data,
                    FieldConfig().add_simple(['status', 'hh_diff_updated']),
                    table_overrides={'margin_l': 4},
                    block_type=block
                ))
                break_section(lines)
            
            # Files that would be updated but are preserved (red warning)
            if hh_diffs_preserved:
                count = len(hh_diffs_preserved)
                category_data = TableData()
                category_data.add_row(
                    'status',
                    value=f'Would be updated but preserved ({count} files)'
                )
                for file_path in sorted(hh_diffs_preserved):
                    category_data.add_row(
                        'hh_diff_preserved',
                        value=safe_str(file_path)
                    )
                lines.append(render_block(
                    category_data,
                    FieldConfig().add_simple(['status', 'hh_diff_preserved']).add_simple_color('hh_diff_preserved', 'red'),
                    table_overrides={'margin_l': 4},
                    block_type=block
                ))
                break_section(lines)
        
        # File differences - Context folder (if context upgrade was requested)
        if has_context_diffs:
            if context_total > 0:
                # Files that will be lost (red)
                if context_diffs_lost:
                    count = len(context_diffs_lost)
                    category_data = TableData()
                    category_data.add_row(
                        'status',
                        value=f'Will be lost ({count} files)'
                    )
                    for file_path in sorted(context_diffs_lost):
                        category_data.add_row(
                            'context_diff_lost',
                            value=safe_str(file_path)
                        )
                    lines.append(render_block(
                        category_data,
                        FieldConfig().add_simple(['status', 'context_diff_lost']).add_simple_color('context_diff_lost', 'red'),
                        table_overrides={'margin_l': 4},
                        block_type=block
                    ))
                    break_section(lines)
                
                # Files that will be restored (green)
                if context_diffs_restored:
                    count = len(context_diffs_restored)
                    category_data = TableData()
                    category_data.add_row(
                        'status',
                        value=f'Will be restored ({count} files)'
                    )
                    for file_path in sorted(context_diffs_restored):
                        category_data.add_row(
                            'context_diff_restored',
                            value=safe_str(file_path)
                        )
                    lines.append(render_block(
                        category_data,
                        FieldConfig().add_simple(['status', 'context_diff_restored']).add_simple_color('context_diff_restored', 'green'),
                        table_overrides={'margin_l': 4},
                        block_type=block
                    ))
                    break_section(lines)
                
                # Files that will be created
                if context_diffs_created:
                    count = len(context_diffs_created)
                    category_data = TableData()
                    category_data.add_row(
                        'status',
                        value=f'Will be created ({count} files)'
                    )
                    for file_path in sorted(context_diffs_created):
                        category_data.add_row(
                            'context_diff_created',
                            value=safe_str(file_path)
                        )
                    lines.append(render_block(
                        category_data,
                        FieldConfig().add_simple(['status', 'context_diff_created']),
                        table_overrides={'margin_l': 4},
                        block_type=block
                    ))
                    break_section(lines)
                
                # Files that will be updated
                if context_diffs_updated:
                    count = len(context_diffs_updated)
                    category_data = TableData()
                    category_data.add_row(
                        'status',
                        value=f'Will be updated ({count} files)'
                    )
                    for file_path in sorted(context_diffs_updated):
                        category_data.add_row(
                            'context_diff_updated',
                            value=safe_str(file_path)
                        )
                    lines.append(render_block(
                        category_data,
                        FieldConfig().add_simple(['status', 'context_diff_updated']),
                        table_overrides={'margin_l': 4},
                        block_type=block
                    ))
                    break_section(lines)
                
                # Files that would be updated but are preserved (red warning)
                if context_diffs_preserved:
                    count = len(context_diffs_preserved)
                    category_data = TableData()
                    category_data.add_row(
                        'status',
                        value=f'Would be updated but preserved ({count} files)'
                    )
                    for file_path in sorted(context_diffs_preserved):
                        category_data.add_row(
                            'context_diff_preserved',
                            value=safe_str(file_path)
                        )
                    lines.append(render_block(
                        category_data,
                        FieldConfig().add_simple(['status', 'context_diff_preserved']).add_simple_color('context_diff_preserved', 'red'),
                        table_overrides={'margin_l': 4},
                        block_type=block
                    ))
                    break_section(lines)
        
        # Reminder messages (only if not dry run)
        if not dry_run:
            upgrade_data.add_row(
                'backup_reminder',
                value='Delete backup directory when satisfied with upgrade'
            )
            upgrade_data.add_row(
                'test_reminder',
                value='Test thoroughly - preserved files may be incompatible with new version'
            )
        
        debug(f"Final upgrade_data: {upgrade_data.num_rows()} items")
        
        # Build field config for main upgrade data (status, backup info, etc.)
        field_config = FieldConfig().add_header('target_header').add_simple(['status'])
        
        if not dry_run:
            field_config.add_simple(['backup_created'])
            if context_backup_name:
                field_config.add_simple(['context_backup_created'])
            field_config.add_simple(['file_restored'])
        
        if not dry_run:
            field_config.add_simple(['backup_reminder', 'test_reminder'])
        
        # Render main upgrade data block
        lines.append(render_block(
            upgrade_data,
            field_config,
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

