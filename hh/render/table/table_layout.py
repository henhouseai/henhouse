from __future__ import annotations
from typing import Dict, List
from hh.render.text.text import display_width
from hh.render.table.table_types import TableConfig, ColumnLayout
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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

def calculate_column_layouts(config: TableConfig, columns: List[str], table_data: Dict[str, List[str]]) -> Dict[str, ColumnLayout]:
    trace_in()
    layouts = {}
    natural_widths: Dict[str, int] = {}
    for c in columns:
        max_line_width = 0
        for s in table_data.get(c, []):
            lines = s.split('\n') if s else ['']
            for line in lines:
                line_width = display_width(line)
                if line_width > max_line_width:
                    max_line_width = line_width
        natural_widths[c] = max_line_width + config.default_padl + config.default_padr
        log(f"Column {c}: natural_width={natural_widths[c]}, content_width={max_line_width}")
    pad_total = config.default_padl + config.default_padr
    assert config.column_widths is not None, "column_widths should be initialized in __post_init__"
    assert config.column_align is not None, "column_align should be initialized in __post_init__"
    assert config.column_overflow is not None, "column_overflow should be initialized in __post_init__"
    assert config.column_valign is not None, "column_valign should be initialized in __post_init__"
    for c in columns:
        w = config.column_widths.get(c, 0)
        if w > 0:
            target_width = w + pad_total
            if natural_widths[c] > target_width:
                wrap_text = True
            else:
                wrap_text = False
            effective_width = min(natural_widths[c], target_width)
            log(f"Column {c}: configured_width={w}, target_width={target_width}, wrap_text={wrap_text}")
        else:
            wrap_text = False
            effective_width = natural_widths[c]
            log(f"Column {c}: using natural width, wrap_text={wrap_text}")
        layouts[c] = ColumnLayout(
            name=c,
            width=w,
            effective_width=effective_width,
            wrap_text=wrap_text,
            align=config.column_align.get(c, 'left'),
            overflow=config.column_overflow.get(c, 'wrap'),
            valign=config.column_valign.get(c, 'top'),
            padding_left=config.default_padl,
            padding_right=config.default_padr
        )
    log(f"Calculated layouts for {len(columns)} columns")
    trace_out()
    return layouts
