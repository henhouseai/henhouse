from __future__ import annotations
from typing import Union, Dict, List, Optional, Tuple
from hh.render.config.config import safe_str
from hh.render.table.table_types import TableConfig, ColumnLayout, RenderedRow
from hh.render.table.table_config import load_table_config, update_column_config, apply_config_overrides
from hh.render.table.table_layout import calculate_column_layouts
from hh.render.table.table_cells import shape_column
from hh.render.table.table_borders import normalize_glyphs, build_top_border, build_header_border, build_mid_border, build_bottom_border
from hh.gateway.gateway import get_gateway
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

class TableBuilder:
    def __init__(self, class_name: str):
        trace_in()
        self.class_name = class_name
        self.columns: Dict[str, List[str]] = {}
        self.column_order: List[str] = []
        self.hrules_after_rows: List[int] = []
        self.config = load_table_config(class_name)
        log(f"TableBuilder initialized for class: {class_name}")
        trace_out()

    def set_columns(self, columns: str) -> 'TableBuilder':
        self.config.columns_order = columns
        column_list = [c.strip() for c in columns.split(',') if c.strip()]
        update_column_config(self.config, column_list)
        return self

    def set_has_header(self, has_header: bool) -> 'TableBuilder':
        self.config.has_header = has_header
        return self

    def set_rule_header(self, rule_header: bool) -> 'TableBuilder':
        self.config.rule_header = rule_header
        return self

    def set_rule_every(self, rule_every: int) -> 'TableBuilder':
        self.config.rule_every = rule_every
        return self

    def set_margin_l(self, margin_l: int) -> 'TableBuilder':
        self.config.margin_l = margin_l
        return self

    def set_margin_r(self, margin_r: int) -> 'TableBuilder':
        self.config.margin_r = margin_r
        return self

    def set_margin_t(self, margin_t: int) -> 'TableBuilder':
        self.config.margin_t = margin_t
        return self

    def set_margin_b(self, margin_b: int) -> 'TableBuilder':
        self.config.margin_b = margin_b
        return self

    def set_padl(self, padl: int) -> 'TableBuilder':
        self.config.default_padl = padl
        return self

    def set_padr(self, padr: int) -> 'TableBuilder':
        self.config.default_padr = padr
        return self

    def set_v_left(self, v_left: str) -> 'TableBuilder':
        self.config.v_left = v_left
        return self

    def set_v_mid(self, v_mid: str) -> 'TableBuilder':
        self.config.v_mid = v_mid
        return self

    def set_v_right(self, v_right: str) -> 'TableBuilder':
        self.config.v_right = v_right
        return self

    def set_h_top(self, h_top: str) -> 'TableBuilder':
        self.config.h_top = h_top
        return self

    def set_h_header(self, h_header: str) -> 'TableBuilder':
        self.config.h_header = h_header
        return self

    def set_h_mid(self, h_mid: str) -> 'TableBuilder':
        self.config.h_mid = h_mid
        return self

    def set_h_bot(self, h_bot: str) -> 'TableBuilder':
        self.config.h_bot = h_bot
        return self

    def set_top_left(self, top_left: str) -> 'TableBuilder':
        self.config.top_left = top_left
        return self

    def set_top_mid(self, top_mid: str) -> 'TableBuilder':
        self.config.top_mid = top_mid
        return self

    def set_top_right(self, top_right: str) -> 'TableBuilder':
        self.config.top_right = top_right
        return self

    def set_mid_left(self, mid_left: str) -> 'TableBuilder':
        self.config.mid_left = mid_left
        return self

    def set_mid_mid(self, mid_mid: str) -> 'TableBuilder':
        self.config.mid_mid = mid_mid
        return self

    def set_mid_right(self, mid_right: str) -> 'TableBuilder':
        self.config.mid_right = mid_right
        return self

    def set_bot_left(self, bot_left: str) -> 'TableBuilder':
        self.config.bot_left = bot_left
        return self

    def set_bot_mid(self, bot_mid: str) -> 'TableBuilder':
        self.config.bot_mid = bot_mid
        return self

    def set_bot_right(self, bot_right: str) -> 'TableBuilder':
        self.config.bot_right = bot_right
        return self

    def set_header_left(self, header_left: str) -> 'TableBuilder':
        self.config.header_left = header_left
        return self

    def set_header_mid(self, header_mid: str) -> 'TableBuilder':
        self.config.header_mid = header_mid
        return self

    def set_header_right(self, header_right: str) -> 'TableBuilder':
        self.config.header_right = header_right
        return self

    def set_column_width(self, column: str, width: int) -> 'TableBuilder':
        assert self.config.column_widths is not None, "column_widths should be initialized in __post_init__"
        self.config.column_widths[column] = width
        return self

    def set_column_align(self, column: str, align: str) -> 'TableBuilder':
        assert self.config.column_align is not None, "column_align should be initialized in __post_init__"
        self.config.column_align[column] = align
        return self

    def set_column_overflow(self, column: str, overflow: str) -> 'TableBuilder':
        assert self.config.column_overflow is not None, "column_overflow should be initialized in __post_init__"
        self.config.column_overflow[column] = overflow
        return self

    def set_column_valign(self, column: str, valign: str) -> 'TableBuilder':
        assert self.config.column_valign is not None, "column_valign should be initialized in __post_init__"
        self.config.column_valign[column] = valign
        return self

    def apply_overrides(self, overrides: Dict[str, Union[str, int, bool]]) -> 'TableBuilder':
        trace_in()
        apply_config_overrides(self.config, overrides)
        log(f"Applied {len(overrides)} overrides: {list(overrides.keys())}")
        trace_out()
        return self

    def cell(self, column: str, value: Union[str, int, float, bool, None]) -> None:
        trace_in()
        if column not in self.columns:
            self.columns[column] = []
            self.column_order.append(column)
            # Load column configuration when a new column is added
            update_column_config(self.config, [column])
            log(f"New column added: {column}")
        self.columns[column].append(safe_str(value))
        log(f"Cell added: column={column}, value={safe_str(value)}")
        trace_out()

    def newline(self, row_index: Optional[int] = None) -> None:
        trace_in()
        if row_index is None:
            target_len = max((len(v) for v in self.columns.values()), default=0)
        else:
            target_len = row_index + 1
        for col in self.columns.keys():
            col_len = len(self.columns[col])
            if col_len < target_len:
                self.columns[col].extend([''] * (target_len - col_len))
        log(f"Newline added: target_length={target_len}, columns={len(self.columns)}")
        trace_out()

    def row(self, pairs: Optional[List[Tuple[str, Union[str, int, float, bool, None]]]] = None, keys: Optional[List[str]] = None, values: Optional[List[Union[str, int, float, bool, None]]] = None) -> None:
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

    def sep(self, kind: str = 'h') -> None:
        trace_in()
        current_rows = max((len(v) for v in self.columns.values()), default=0)
        if current_rows > 0:
            self.hrules_after_rows.append(current_rows - 1)
            log(f"Separator added: kind={kind}, after_row={current_rows - 1}")
        else:
            log("No rows to separate")
        trace_out()

    def render(self, class_name: Optional[str] = None) -> str:
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available")
            trace_out()
            return ""
        cls = class_name or self.class_name
        cfg_order = self.config.columns_order
        if cfg_order:
            order = [c.strip() for c in cfg_order.split(',') if c.strip()]
        else:
            order = list(self.column_order)
        for c in order:
            if c not in self.columns:
                self.columns[c] = []
        self.newline()
        num_rows = max((len(v) for v in self.columns.values()), default=0)
        column_layouts = calculate_column_layouts(self.config, order, self.columns)
        glyphs = normalize_glyphs(self.config)
        lines_out: List[str] = []
        log(f"Rendering table: class={cls}, columns={len(order)}, rows={num_rows}")
        for _ in range(self.config.margin_t):
            lines_out.append('')
        top_border = build_top_border(glyphs, column_layouts, order)
        if top_border:
            lines_out.append((' ' * self.config.margin_l) + top_border + (' ' * self.config.margin_r))
        start_row = 0
        gateway = get_gateway()
        if gateway and self.config.has_header and num_rows > 0 and not gateway.is_no('header'):
            header_lines = self._render_data_row(0, order, column_layouts, glyphs)
            lines_out.extend([(' ' * self.config.margin_l) + ln + (' ' * self.config.margin_r) for ln in header_lines])
            start_row = 1
            if self.config.rule_header and not gateway.is_no('header'):
                header_border = build_header_border(glyphs, column_layouts, order)
                if header_border:
                    lines_out.append((' ' * self.config.margin_l) + header_border + (' ' * self.config.margin_r))
        assert self.config.separator_after_rows is not None, "separator_after_rows should be initialized in __post_init__"
        assert self.config.separator_after_rows is not None, "separator_after_rows should be initialized in __post_init__"
        for r in range(start_row, num_rows):
            row_lines = self._render_data_row(r, order, column_layouts, glyphs)
            lines_out.extend([(' ' * self.config.margin_l) + ln + (' ' * self.config.margin_r) for ln in row_lines])
            should_rule = (r in self.hrules_after_rows) or (r in self.config.separator_after_rows) or (self.config.rule_every > 0 and r < num_rows - 1 and ((r - start_row + 1) % self.config.rule_every == 0))
            if should_rule:
                mid_border = build_mid_border(glyphs, column_layouts, order)
                if mid_border:
                    lines_out.append((' ' * self.config.margin_l) + mid_border + (' ' * self.config.margin_r))
        bottom_border = build_bottom_border(glyphs, column_layouts, order)
        if bottom_border:
            lines_out.append((' ' * self.config.margin_l) + bottom_border + (' ' * self.config.margin_r))
        for _ in range(self.config.margin_b):
            lines_out.append('')
        result = "\n".join(lines_out)
        log(f"Table rendered: {len(lines_out)} lines, {len(result)} characters")
        trace_out()
        return result

    def _render_data_row(self, row_index: int, order: List[str], column_layouts: Dict[str, ColumnLayout], glyphs: Dict[str, str]) -> List[str]:
        trace_in()
        shaped_columns: Dict[str, Dict[str, List[str]]] = {}
        max_h = 1
        for c in order:
            txt = self.columns[c][row_index] if row_index < len(self.columns[c]) else ''
            layout = column_layouts[c]
            shaped = shape_column(c, [txt], layout)
            shaped_columns[c] = shaped
            if len(shaped["row_0"]) > max_h:
                max_h = len(shaped["row_0"])
        lines_out: List[str] = []
        for i in range(max_h):
            segs: List[str] = []
            segs.append(glyphs['v_left'])
            for idx, c in enumerate(order):
                cell_lines = shaped_columns[c]["row_0"]
                if i < len(cell_lines):
                    segs.append(cell_lines[i])
                else:
                    segs.append(' ' * column_layouts[c].effective_width)
                if idx < len(order) - 1:
                    segs.append(glyphs['v_mid'])
            segs.append(glyphs['v_right'])
            lines_out.append(''.join(segs))
        log(f"Data row rendered: row={row_index}, height={max_h}, columns={len(order)}")
        trace_out()
        return lines_out
