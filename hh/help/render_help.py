from __future__ import annotations
from typing import Any, Dict, List
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section
from hh.gateway.response.json_standard import get_data
from hh.gateway.gateway import get_gateway
from hh.help.help_query import HelpQuery
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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


def _render_special_file_help(lines: List[str], topic: str, sections: Dict[str, Any]) -> None:
    trace_in()
    log(f"Rendering special file help for topic: {topic}")
    main_table_data = TableData()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no('header'):
        main_content = sections.get('main', '')
        main_table_data.add_row(
            'help_topic',
            section=topic,
            content=main_content
        )
        log(f"Added main content header for topic: {topic}")
    children = sections.get('children', {})
    log(f"Found {len(children)} child directories")
    for child_name, child_desc in children.items():
        main_table_data.add_row(
            'help_child',
            section=child_name,
            content=child_desc
        )
        log(f"Added child directory: {child_name}")
    if main_table_data.num_rows() > 0:
        lines.append(render_block(
            main_table_data,
            FieldConfig()
                .add_header('help_topic')
                .add_simple(['help_child']),
            table_overrides={
                'margin_l': 4,
                'column_align': {'label': 'right'},
                'rule_every': 1
            },
            block_type='summary'
        ))
        break_section(lines)
        log(f"Rendered main table with {main_table_data.num_rows()} rows")
    files = sections.get('files', {})
    log(f"Found {len(files)} individual files to render")
    for file_name, file_summary in files.items():
        _render_individual_file_table(lines, file_name, file_summary)
    trace_out()

def _render_individual_file_table(lines: List[str], file_name: str, file_summary: str) -> None:
    trace_in()
    log(f"Rendering individual file table for: {file_name}")
    try:
        help_query = HelpQuery(file_name)
        file_sections = help_query.sections
        log(f"Found {len(file_sections)} sections in file: {file_name}")
        table_data = TableData()
        table_data.add_row(
            'help_file_header',
            section=file_name,
            content=file_summary
        )
        log(f"Added file header for: {file_name}")
        for section_name, section_content in file_sections.items():
            if section_name != file_name:
                try:
                    desc_content = help_query.get_section_description(file_name, section_name)
                    if desc_content and not desc_content.startswith("Section"):
                        table_data.add_row(
                            'help_section_desc',
                            section=section_name,
                            content=desc_content
                        )
                        log(f"Added section description: {section_name}")
                except Exception as e:
                    warn(f"Failed to get section description for {section_name}: {e}")
                    continue
        if table_data.num_rows() > 1:
            lines.append(render_block(
                table_data,
                FieldConfig()
                    .add_header('help_file_header')
                    .add_simple(['help_section_desc']),
                table_overrides={
                    'margin_l': 4,
                    'column_align': {'label': 'right'},
                    'rule_every': 1
                },
                block_type='rows'
            ))
            break_section(lines)
            log(f"Rendered individual file table with {table_data.num_rows()} rows")
        else:
            log(f"Skipping file table for {file_name} - insufficient data")
    except Exception as e:
        warn(f"Failed to render individual file table for {file_name}: {e}")
    trace_out()

def _render_regular_help(lines: List[str], topic: str, sections: Dict[str, Any]) -> None:
    trace_in()
    log(f"Rendering regular help for topic: {topic}")
    table_data = TableData()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_no('header'):
        special_section_content = sections.get(topic, '')
        table_data.add_row(
            'help_topic',
            section=topic,
            content=special_section_content
        )
        log(f"Added topic header for: {topic}")
    log(f"Found {len(sections)} sections to process")
    for section_name, section_content in sections.items():
        if section_name == topic:
            continue
        table_data.add_row(
            'help_section',
            section=section_name,
            content=section_content
        )
        log(f"Added section: {section_name}")
    lines.append(render_block(
        table_data,
        FieldConfig()
            .add_header('help_topic')
            .add_simple(['help_section']),
        table_overrides={
            'margin_l': 4,
            'column_align': {'label': 'right'},
            'rule_every': 1
        },
        block_type='summary'
    ))
    break_section(lines)
    log(f"Rendered regular help table with {table_data.num_rows()} rows")
    trace_out()

@register_http('help')
@register_parser('help')
def help() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend","No action response available")
        trace_out()
        return False
    
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data)
    
    lines = []
    lines.append(render_header_block('l_help_header'))
    log("Added help header block")
    
    log(f"Extracted source data: {type(source_data)}")
    topic = None
    sections = {}
    for key, value in source_data.items():
        if isinstance(value, dict):
            topic = key
            sections = value
            break
    if not topic:
        log("No topic found in source data")
        report_error("backend","No topic found in source data")
        trace_out()
        return False
    
    log(f"Found topic: {topic} with {len(sections)} sections")
    if 'main' in sections or 'children' in sections or 'files' in sections:
        log("Rendering special file help")
        _render_special_file_help(lines, topic, sections)
    else:
        log("Rendering regular help")
        _render_regular_help(lines, topic, sections)
    
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Finalized output with {len(lines)} lines")
    trace_out()
    return True
