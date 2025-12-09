from __future__ import annotations
from typing import Dict, List, Union, TypedDict, Optional
from hh.render.config.config import ic, dc, break_section
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.backend import BACKEND_TYPES

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

class FieldConfigItem(TypedDict, total=False):
    field_type: str
    label_key: str
    icon_key: str
    no_flag: str
    condition: callable


class FieldConfig:
    def __init__(self):
        self.configs: List[FieldConfigItem] = []
    
    def add_header(self, header_name: str) -> 'FieldConfig':
        self.configs.append({
            'field_type': header_name,
            'label_key': f'l_{header_name}',
            'icon_key': header_name,
            'no_flag': 'header'
        })
        return self
    
    def add_headers(self, header_names: List[str]) -> 'FieldConfig':
        for header_name in header_names:
            self.add_header(header_name)
        return self
    
    def add_simple(self, field_names: List[str]) -> 'FieldConfig':
        for name in field_names:
            self.configs.append({
                'field_type': name,
                'label_key': f'l_{name}',
                'icon_key': name,
                'no_flag': name
            })
        return self
    
    def add_group(self, field_names: List[str], shared_no_flag: str) -> 'FieldConfig':
        for name in field_names:
            self.configs.append({
                'field_type': name,
                'label_key': f'l_{name}',
                'icon_key': name,
                'no_flag': shared_no_flag
            })
        return self
    
    def addGroup(self, field_names: List[str], shared_no_flag: str) -> 'FieldConfig':
        return self.add_group(field_names, shared_no_flag)
    
    def add_simple_color(self, field_name: str, color: str) -> 'FieldConfig':
        self.configs.append({
            'field_type': field_name,
            'label_key': f'l_{field_name}',
            'icon_key': field_name,
            'color_key': color,
            'no_flag': field_name
        })
        return self
    
    def get_configs(self) -> List[FieldConfigItem]:
        return self.configs

class TableRow(TypedDict, total=False):
    field_type: str
    label: str

class TableData:
    def __init__(self):
        self.rows: List[TableRow] = []
        self.gateway = get_gateway()
    
    def add_row(self, field_type: str, **extra_cols) -> 'TableData':
        row = {
            'field_type': field_type,
            'label': ''
        }
        # Add any extra columns
        for key, val in extra_cols.items():
            row[key] = val
        self.rows.append(row)
        return self
    
    def add_page_link_to_column(self, column_name: str, page_id: int) -> 'TableData':
        """Add page link metadata to the specified column of the most recently added row."""
        if not self.rows:
            return self
        last_row = self.rows[-1]
        if '_links' not in last_row:
            last_row['_links'] = {}
        last_row['_links'][column_name] = {'type': 'page', 'id': page_id}
        return self
    
    def add_image_link_to_column(self, column_name: str, image_id: int) -> 'TableData':
        """Add image link metadata to the specified column of the most recently added row."""
        if not self.rows:
            return self
        last_row = self.rows[-1]
        if '_links' not in last_row:
            last_row['_links'] = {}
        last_row['_links'][column_name] = {'type': 'image', 'id': image_id}
        return self
    
    def add_image_file_link_to_column(self, column_name: str, src_path: str) -> 'TableData':
        """Add image file link metadata to the specified column of the most recently added row."""
        if not self.rows:
            return self
        last_row = self.rows[-1]
        if '_links' not in last_row:
            last_row['_links'] = {}
        last_row['_links'][column_name] = {'type': 'image_file', 'src_path': src_path}
        return self
    
    def add_file_link_to_column(self, column_name: str, file_id: int) -> 'TableData':
        """Add file link metadata (by file_id) to the specified column of the most recently added row."""
        if not self.rows:
            return self
        last_row = self.rows[-1]
        if '_links' not in last_row:
            last_row['_links'] = {}
        last_row['_links'][column_name] = {'type': 'file', 'id': file_id}
        return self
    
    def num_rows(self) -> int:
        if self.gateway and self.gateway.is_no('header') and len(self.rows) > 1:
            return len(self.rows) - 1
        return len(self.rows)
    
    def get_rows(self) -> List[TableRow]:
        if self.gateway and self.gateway.is_no('header') and len(self.rows) > 1:
            return self.rows[1:]
        return self.rows

def finalize_output(lines: List[str]) -> str:
    trace_in()
    filtered_lines = [line for line in lines if line and (line.strip() or line == "\n")]
    processed_lines = ["" if line == "\n" else line for line in filtered_lines]
    result = "\n".join(processed_lines)
    log(f"Finalized output: {len(lines)} input lines -> {len(processed_lines)} output lines")
    trace_out()
    return result

def render_header_block(subheader_key: str, header_id: str = None) -> str:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    # Convert None to empty string for downstream functions
    if header_id is None:
        header_id = ""
    
    # Check backend type and lazy import appropriate renderer
    backend = gateway.backend if hasattr(gateway, 'backend') else None
    if backend == "http":
        log("HTTP backend detected, using HTML header renderer")
        from hh.render.render_http import render_html_header
        result = render_html_header(subheader_key, header_id)
    else:
        from hh.render.render_parser import render_parser_header
        result = render_parser_header(subheader_key, header_id)
    trace_out()
    return result

def render_block(
    table_data: TableData, 
    field_configs: FieldConfig = None, 
    table_class: str = 'standard',
    table_overrides: Dict[str, Union[str, int, bool]] = None,
    block_type: str = None,
    backend: Optional[str] = None,
    wrapper_id: Optional[str] = None,
    wrapper_extra_classes: Optional[str] = None
) -> str:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    log(f"Rendering block: {table_data.num_rows()} rows, table_class={table_class}, block_type={block_type}, wrapper_id={wrapper_id}")
    if block_type and gateway.is_no(block_type):
        log(f"Block type '{block_type}' disabled, returning empty")
        trace_out()
        return ""
    if table_data.num_rows() == 0:
        log("No data to render")
        trace_out()
        return ""
    if block_type == 'meta':
        log("Rendering meta table")
        # Lazy import parser module for meta tables
        from hh.render.render_parser import render_meta_table
        meta_table_overrides = {'padl': 2,'padr': 2, 'column_align': {'label': 'right'}}
        if table_overrides:
            meta_table_overrides.update(table_overrides)
        result = render_meta_table(
            table_data, 
            FieldConfig()
                .add_header('meta_header')
                .add_simple(['meta', 'sub_meta']), 
            table_class, 
            meta_table_overrides,
            'div'
        )
        trace_out()
        return result
    
    # Check backend type and lazy import appropriate renderer
    # If backend parameter is provided and valid, use it; otherwise fall back to gateway.backend
    if backend is not None:
        if backend in BACKEND_TYPES:
            log(f"Using override backend: {backend}")
        else:
            warn(f"Invalid backend override '{backend}', falling back to gateway.backend")
            backend = gateway.backend if hasattr(gateway, 'backend') else None
    else:
        backend = gateway.backend if hasattr(gateway, 'backend') else None
    
    if backend == "http":
        log("HTTP backend detected, using HTML renderer")
        from hh.render.render_http import render_html_table
        result = render_html_table(table_data, field_configs, table_class, table_overrides, wrapper_id=wrapper_id, wrapper_extra_classes=wrapper_extra_classes)
    else:
        from hh.render.render_parser import render_flexible_table
        result = render_flexible_table(table_data, field_configs, table_class, table_overrides)
    trace_out()
    return result
