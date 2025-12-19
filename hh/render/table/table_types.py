from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass
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

@dataclass
class TableConfig:
    class_name: str
    columns_order: str = ''
    has_header: bool = False
    rule_header: bool = False
    rule_every: int = 0
    margin_l: int = 0
    margin_r: int = 0
    margin_t: int = 0
    margin_b: int = 0
    default_padl: int = 1
    default_padr: int = 1
    v_left: str = ''
    v_mid: str = ''
    v_right: str = ''
    h_top: str = ''
    h_header: str = ''
    h_mid: str = ''
    h_bot: str = ''
    top_left: str = ''
    top_mid: str = ''
    top_right: str = ''
    mid_left: str = ''
    mid_mid: str = ''
    mid_right: str = ''
    bot_left: str = ''
    bot_mid: str = ''
    bot_right: str = ''
    header_left: str = ''
    header_mid: str = ''
    header_right: str = ''
    column_widths: Optional[Dict[str, int]] = None
    column_align: Optional[Dict[str, str]] = None
    column_overflow: Optional[Dict[str, str]] = None
    column_valign: Optional[Dict[str, str]] = None
    separator_after_rows: Optional[List[int]] = None
    
    def __post_init__(self):
        trace_in()
        if self.column_widths is None:
            self.column_widths = {}
        if self.column_align is None:
            self.column_align = {}
        if self.column_overflow is None:
            self.column_overflow = {}
        if self.column_valign is None:
            self.column_valign = {}
        if self.separator_after_rows is None:
            self.separator_after_rows = []
        log(f"TableConfig initialized for class: {self.class_name}")
        trace_out()

@dataclass
class ColumnLayout:
    name: str
    width: int
    effective_width: int
    wrap_text: bool
    align: str
    overflow: str
    valign: str
    padding_left: int
    padding_right: int

@dataclass
class RenderedRow:
    lines: List[str]
    vertical_types: List[List[str]]
