from __future__ import annotations
import html
from typing import Dict, List, Union, Optional
from hh.render.config.config import safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.html.color_converter import get_uniform_row_color, get_uniform_cell_color, convert_ansi_to_html
from hh.render.text.color import strip_ansi, has_color_codes

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(False)
    trace_out = get_trace_out(False)
    log = get_log(False)
    debug = get_debug(False)
    warn = get_warn(True)

class HtmlTableBuilder:
    """HTML table builder - mirrors TableBuilder API but outputs HTML."""
    
    def __init__(self, class_name: str, table_id: str):
        trace_in()
        self.class_name = class_name  # Store for potential future use
        self.table_id = table_id  # Unique identifier for DOM access
        self.columns: Dict[str, List[str]] = {}  # column_name -> list of cell values
        self.column_order: List[str] = []  # Order of columns
        self.config = {
            'columns_order': '',
            'has_header': False,
            'column_widths': {},
            'column_overflow': {},
            'column_align': {},
            'margin_l': 0,
            'margin_r': 0,
            'margin_t': 0,
            'margin_b': 0,
        }
        log(f"HtmlTableBuilder initialized for class: {class_name}, table_id: {table_id}")
        trace_out()
    
    def set_columns(self, columns: str) -> 'HtmlTableBuilder':
        """Set column order from comma-separated string."""
        trace_in()
        self.config['columns_order'] = columns
        column_list = [c.strip() for c in columns.split(',') if c.strip()]
        # Initialize columns dict
        for col in column_list:
            if col not in self.columns:
                self.columns[col] = []
                self.column_order.append(col)
        log(f"Columns set: {column_list}")
        trace_out()
        return self
    
    def set_has_header(self, has_header: bool) -> 'HtmlTableBuilder':
        """Set whether table has a header row."""
        self.config['has_header'] = has_header
        return self
    
    def set_column_width(self, column: str, width: int) -> 'HtmlTableBuilder':
        """Store column width (not used in Phase 1, stored for future)."""
        self.config['column_widths'][column] = width
        return self
    
    def set_column_overflow(self, column: str, overflow: str) -> 'HtmlTableBuilder':
        """Store column overflow setting (not used in Phase 1, stored for future)."""
        self.config['column_overflow'][column] = overflow
        return self
    
    def set_column_align(self, column: str, align: str) -> 'HtmlTableBuilder':
        """Store column alignment (not used in Phase 1, stored for future)."""
        self.config['column_align'][column] = align
        return self
    
    def apply_overrides(self, overrides: Dict[str, Union[str, int, bool]]) -> 'HtmlTableBuilder':
        """Apply configuration overrides (stored for future use, minimal for Phase 1)."""
        trace_in()
        # Store basic overrides in config
        if 'has_header' in overrides:
            self.config['has_header'] = overrides['has_header']
        if 'column_widths' in overrides:
            self.config['column_widths'].update(overrides['column_widths'])
        if 'column_align' in overrides:
            self.config['column_align'].update(overrides['column_align'])
        log(f"Applied {len(overrides)} overrides")
        trace_out()
        return self
    
    def cell(self, column: str, value: Union[str, int, float, bool, None]) -> None:
        """Add a cell value to a column."""
        trace_in()
        if column not in self.columns:
            self.columns[column] = []
            self.column_order.append(column)
        self.columns[column].append(safe_str(value))
        log(f"Cell added: column={column}, value={safe_str(value)}")
        trace_out()
    
    def newline(self, row_index: Optional[int] = None) -> None:
        """Ensure all columns have same number of rows (pad with empty strings)."""
        trace_in()
        if row_index is None:
            target_len = max((len(v) for v in self.columns.values()), default=0)
        else:
            target_len = row_index + 1
        for col in self.columns.keys():
            col_len = len(self.columns[col])
            if col_len < target_len:
                self.columns[col].extend([''] * (target_len - col_len))
        log(f"Newline: target_length={target_len}")
        trace_out()
    
    def row(self, pairs: Optional[List] = None, keys: Optional[List[str]] = None, values: Optional[List] = None) -> None:
        """Add a row of data."""
        trace_in()
        self.newline()
        if pairs is not None:
            for k, v in pairs:
                self.cell(k, v)
            log(f"Row added via pairs: {len(pairs)} cells")
        elif keys is not None and values is not None:
            for k, v in zip(keys, values):
                self.cell(k, v)
            log(f"Row added via keys/values: {len(keys)} cells")
        self.newline()
        trace_out()
    
    def render(self) -> str:
        """Render the table as HTML."""
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available")
            trace_out()
            return ""
        
        # Get column order
        if self.config['columns_order']:
            column_list = [c.strip() for c in self.config['columns_order'].split(',') if c.strip()]
        else:
            column_list = list(self.column_order)
        
        # Ensure all columns exist
        for col in column_list:
            if col not in self.columns:
                self.columns[col] = []
        
        # Calculate number of rows
        num_rows = max((len(v) for v in self.columns.values()), default=0)
        if num_rows == 0:
            log("No rows to render")
            trace_out()
            return ""
        
        log(f"Rendering HTML table: {len(column_list)} columns, {num_rows} rows")
        
        # Start building HTML - add ID to parent div if provided
        div_tag = '<div class="content tableViewDiv"'
        if self.table_id:
            escaped_id = html.escape(str(self.table_id), quote=True)
            div_tag += f' id="{escaped_id}"'
        div_tag += '>\n'
        html_parts = [div_tag]
        table_tag = '  <table class="pageTableView" cellpadding="0" cellspacing="0">\n'
        html_parts.append(table_tag)
        
        # Header row (only if explicitly enabled, matching CLI behavior)
        has_header = self.config.get('has_header', False)  # Default to False to match CLI
        if has_header:
            html_parts.append('    <thead>\n      <tr>\n')
            for i, col in enumerate(column_list):
                # First column is always 'label', others use column name
                css_class = 'label' if i == 0 else col
                html_parts.append(f'        <th class="{css_class}">{col}</th>\n')
            html_parts.append('      </tr>\n    </thead>\n')
        
        # Body rows
        html_parts.append('    <tbody>\n')
        for row_idx in range(num_rows):
            # Determine odd/even class (no row-level colors - always use cell-level)
            row_class = 'odd' if (row_idx % 2 == 0) else 'even'
            html_parts.append(f'      <tr class="{row_class}">\n')
            
            for i, col in enumerate(column_list):
                # First column is always 'label', others use column name
                css_class = 'label' if i == 0 else col
                
                # Get cell value
                cell_value = ""
                if col in self.columns and row_idx < len(self.columns[col]):
                    cell_value = self.columns[col][row_idx] or ""
                
                cell_str = str(cell_value)
                
                # Process color conversion - always use cell-level or inline spans
                if has_color_codes(cell_str):
                    # Check for cell-level uniform color
                    cell_color = get_uniform_cell_color(cell_str)
                    if cell_color:
                        # Entire cell is one color - apply to <td> class
                        css_class += f' color-{cell_color}'
                        converted_value = strip_ansi(cell_str)
                        escaped_value = converted_value
                    else:
                        # Mixed colors - convert to <span> tags
                        escaped_value = convert_ansi_to_html(cell_str)
                else:
                    # No color codes, pass through without escaping
                    escaped_value = cell_str
                
                html_parts.append(f'        <td class="{css_class}">{escaped_value}</td>\n')
            
            html_parts.append('      </tr>\n')
        
        html_parts.append('    </tbody>\n')
        html_parts.append('  </table>\n')
        html_parts.append('</div>\n')
        
        result = ''.join(html_parts)
        log(f"HTML table rendered: {len(result)} characters")
        trace_out()
        return result

