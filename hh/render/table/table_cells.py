from __future__ import annotations
from typing import Dict, List
from hh.render.text.text import display_width, wrap, ellipsize, slice
from hh.render.table.table_types import ColumnLayout
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

def shape_cell(layout: ColumnLayout, text: str) -> List[str]:
    trace_in()
    if not layout.wrap_text:
        result = text.split('\n') if text else ['']
        log(f"Cell shaping: no wrap, {len(result)} lines")
        trace_out()
        return result
    content_width = layout.effective_width - layout.padding_left - layout.padding_right
    overflow = layout.overflow
    lines = text.split('\n') if text else ['']
    result = []
    for line in lines:
        if overflow == 'wrap':
            wrapped_lines = wrap(line, content_width)
            result.extend(wrapped_lines)
        elif overflow == 'ellipsis':
            result.append(ellipsize(line, content_width))
        elif overflow == 'clip':
            result.append(slice(line, content_width))
        else:
            wrapped_lines = wrap(line, content_width)
            result.extend(wrapped_lines)
    log(f"Cell shaping: overflow={overflow}, content_width={content_width}, result_lines={len(result)}")
    trace_out()
    return result

def align_line(layout: ColumnLayout, line: str) -> str:
    trace_in()
    if layout.effective_width <= 0:
        log("align_line: effective_width <= 0, returning original line")
        trace_out()
        return line
    content_width = layout.effective_width - layout.padding_left - layout.padding_right
    align = layout.align
    lw = display_width(line)
    if content_width <= 0:
        core = ''
    else:
        if align == 'right':
            core = ' ' * max(0, content_width - lw) + line
        elif align == 'center':
            left = max(0, (content_width - lw) // 2)
            right = max(0, content_width - lw - left)
            core = (' ' * left) + line + (' ' * right)
        else:
            core = line + (' ' * max(0, content_width - lw))
    result = (' ' * layout.padding_left) + core + (' ' * layout.padding_right)
    log(f"Line alignment: align={align}, line_width={lw}, content_width={content_width}")
    trace_out()
    return result

def shape_column(column_name: str, rows: List[str], layout: ColumnLayout) -> Dict[str, List[str]]:
    trace_in()
    shaped: Dict[str, List[str]] = {}
    max_h = 1
    for row_idx, text in enumerate(rows):
        lines = shape_cell(layout, text)
        shaped[f"row_{row_idx}"] = lines
        if len(lines) > max_h:
            max_h = len(lines)
    log(f"Column {column_name}: max_height={max_h}, rows={len(rows)}")
    out_blocks: Dict[str, List[str]] = {}
    for row_idx, text in enumerate(rows):
        lines = shaped[f"row_{row_idx}"]
        lines = [align_line(layout, ln) for ln in lines]
        pad_line = ' ' * layout.effective_width if layout.effective_width > 0 else ''
        if len(lines) < max_h:
            pad_needed = max_h - len(lines)
            if layout.valign == 'bot':
                lines = [pad_line] * pad_needed + lines
            elif layout.valign == 'center':
                top = pad_needed // 2
                bot = pad_needed - top
                lines = [' ' * layout.effective_width] * top + lines + [' ' * layout.effective_width] * bot
            else:
                lines = lines + [pad_line] * pad_needed
        out_blocks[f"row_{row_idx}"] = lines
    log(f"Column {column_name}: valign={layout.valign}, final_height={max_h}")
    trace_out()
    return out_blocks
