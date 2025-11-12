from __future__ import annotations
from typing import List, Dict
from hh.render.text.text import display_width, pad_center, pad_left, pad_right
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

def normalize_glyphs(config: TableConfig) -> Dict[str, str]:
    trace_in()
    center_elements = [
        config.top_mid,
        config.mid_mid,
        config.bot_mid,
        config.v_mid,
        config.h_header,
        config.header_mid
    ]
    center_max_width = max(display_width(elem) for elem in center_elements)
    center_default = ' ' * center_max_width
    log(f"Center elements max width: {center_max_width}")
    top_mid = pad_center(config.top_mid, center_max_width) if config.top_mid else center_default
    mid_mid = pad_center(config.mid_mid, center_max_width) if config.mid_mid else center_default
    bot_mid = pad_center(config.bot_mid, center_max_width) if config.bot_mid else center_default
    v_mid = pad_center(config.v_mid, center_max_width)
    header_mid = pad_center(config.header_mid, center_max_width) if config.header_mid else center_default
    left_elements = [
        config.top_left,
        config.mid_left,
        config.bot_left,
        config.v_left,
        config.header_left
    ]
    left_max_width = max(display_width(elem) for elem in left_elements)
    left_default = ' ' * left_max_width
    log(f"Left elements max width: {left_max_width}")
    top_left = pad_right(config.top_left, left_max_width) if config.top_left else left_default
    mid_left = pad_right(config.mid_left, left_max_width) if config.mid_left else left_default
    bot_left = pad_right(config.bot_left, left_max_width) if config.bot_left else left_default
    v_left = pad_right(config.v_left, left_max_width)
    header_left = pad_right(config.header_left, left_max_width) if config.header_left else left_default
    right_elements = [
        config.top_right,
        config.mid_right,
        config.bot_right,
        config.v_right,
        config.header_right
    ]
    right_max_width = max(display_width(elem) for elem in right_elements)
    right_default = ' ' * right_max_width
    log(f"Right elements max width: {right_max_width}")
    top_right = pad_left(config.top_right, right_max_width) if config.top_right else right_default
    mid_right = pad_left(config.mid_right, right_max_width) if config.mid_right else right_default
    bot_right = pad_left(config.bot_right, right_max_width) if config.bot_right else right_default
    v_right = pad_left(config.v_right, right_max_width)
    header_right = pad_left(config.header_right, right_max_width) if config.header_right else right_default
    top_row_has_content = any(elem and elem.strip() for elem in [top_left, top_mid, top_right])
    if top_row_has_content:
        top_left = top_left if top_left else ' '
        top_mid = top_mid if top_mid else ' '
        top_right = top_right if top_right else ' '
        h_top = config.h_top if config.h_top else ' '
    else:
        h_top = config.h_top
    center_row_has_content = any(elem and elem.strip() for elem in [mid_left, mid_mid, mid_right])
    if center_row_has_content:
        mid_left = mid_left if mid_left else ' '
        mid_mid = mid_mid if mid_mid else ' '
        mid_right = mid_right if mid_right else ' '
        h_mid = config.h_mid if config.h_mid else ' '
    else:
        h_mid = config.h_mid
    header_row_has_content = any(elem and elem.strip() for elem in [header_left, header_mid, header_right])
    if header_row_has_content:
        header_left = header_left if header_left else ' '
        header_mid = header_mid if header_mid else ' '
        header_right = header_right if header_right else ' '
        h_header = config.h_header if config.h_header else ' '
    else:
        h_header = config.h_header
    bot_row_has_content = any(elem and elem.strip() for elem in [bot_left, bot_mid, bot_right])
    if bot_row_has_content:
        bot_left = bot_left if bot_left else ' '
        bot_mid = bot_mid if bot_mid else ' '
        bot_right = bot_right if bot_right else ' '
        h_bot = config.h_bot if config.h_bot else ' '
    else:
        h_bot = config.h_bot
    has_space = any(elem == " " for elem in [v_left, top_left, mid_left, bot_left, header_left])
    has_non_space = any(elem != "" and elem != " " for elem in [v_left, top_left, mid_left, bot_left, header_left])
    if has_space and not has_non_space:
        v_left = top_left = mid_left = bot_left = header_left = ""
    has_space = any(elem == " " for elem in [v_mid, top_mid, mid_mid, bot_mid, header_mid])
    has_non_space = any(elem != "" and elem != " " for elem in [v_mid, top_mid, mid_mid, bot_mid, header_mid])
    if has_space and not has_non_space:
        v_mid = top_mid = mid_mid = bot_mid = header_mid = ""
    has_space = any(elem == " " for elem in [v_right, top_right, mid_right, bot_right, header_right])
    has_non_space = any(elem != "" and elem != " " for elem in [v_right, top_right, mid_right, bot_right, header_right])
    if has_space and not has_non_space:
        v_right = top_right = mid_right = bot_right = header_right = ""
    log(f"Glyph normalization completed: center_width={center_max_width}, left_width={left_max_width}, right_width={right_max_width}")
    trace_out()
    return {
        'v_left': v_left,
        'v_mid': v_mid,
        'v_right': v_right,
        'h_top': h_top,
        'h_header': h_header,
        'h_mid': h_mid,
        'h_bot': h_bot,
        'top_left': top_left,
        'top_mid': top_mid,
        'top_right': top_right,
        'mid_left': mid_left,
        'mid_mid': mid_mid,
        'mid_right': mid_right,
        'bot_left': bot_left,
        'bot_mid': bot_mid,
        'bot_right': bot_right,
        'header_left': header_left,
        'header_mid': header_mid,
        'header_right': header_right
    }

def build_top_border(glyphs: Dict[str, str], column_layouts: Dict[str, ColumnLayout], column_order: List[str]) -> str:
    trace_in()
    if not any(g.strip() for g in [glyphs['top_left'], glyphs['top_mid'], glyphs['top_right']]) and not glyphs['h_top']:
        log("No top border elements, returning empty string")
        trace_out()
        return ""
    segs = []
    segs.append(glyphs['top_left'])
    for idx, c in enumerate(column_order):
        width = column_layouts[c].effective_width
        pat = glyphs['h_top']
        if width > 0 and pat:
            reps = (width + len(pat) - 1) // len(pat)
            fill = (pat * reps)[:width]
        else:
            fill = '' if width == 0 else '-' * width if pat else ''
        segs.append(fill)
        if idx < len(column_order) - 1:
            segs.append(glyphs['top_mid'])
    segs.append(glyphs['top_right'])
    result = ''.join(segs)
    log(f"Top border built: length={len(result)}, columns={len(column_order)}")
    trace_out()
    return result

def build_header_border(glyphs: Dict[str, str], column_layouts: Dict[str, ColumnLayout], column_order: List[str]) -> str:
    trace_in()
    if not any(g.strip() for g in [glyphs['header_left'], glyphs['header_mid'], glyphs['header_right']]) and not glyphs['h_header']:
        log("No header border elements, returning empty string")
        trace_out()
        return ""
    segs = []
    segs.append(glyphs['header_left'])
    for idx, c in enumerate(column_order):
        width = column_layouts[c].effective_width
        pat = glyphs['h_header']
        if width > 0 and pat:
            reps = (width + len(pat) - 1) // len(pat)
            fill = (pat * reps)[:width]
        else:
            fill = '' if width == 0 else '-' * width if pat else ''
        segs.append(fill)
        if idx < len(column_order) - 1:
            segs.append(glyphs['header_mid'])
    segs.append(glyphs['header_right'])
    result = ''.join(segs)
    log(f"Header border built: length={len(result)}, columns={len(column_order)}")
    trace_out()
    return result

def build_mid_border(glyphs: Dict[str, str], column_layouts: Dict[str, ColumnLayout], column_order: List[str]) -> str:
    trace_in()
    if not any(g.strip() for g in [glyphs['mid_left'], glyphs['mid_mid'], glyphs['mid_right']]) and not glyphs['h_mid']:
        log("No mid border elements, returning empty string")
        trace_out()
        return ""
    segs = []
    segs.append(glyphs['mid_left'])
    for idx, c in enumerate(column_order):
        width = column_layouts[c].effective_width
        pat = glyphs['h_mid']
        if width > 0 and pat:
            reps = (width + len(pat) - 1) // len(pat)
            fill = (pat * reps)[:width]
        else:
            fill = '' if width == 0 else '-' * width if pat else ''
        segs.append(fill)
        if idx < len(column_order) - 1:
            segs.append(glyphs['mid_mid'])
    segs.append(glyphs['mid_right'])
    result = ''.join(segs)
    log(f"Mid border built: length={len(result)}, columns={len(column_order)}")
    trace_out()
    return result

def build_bottom_border(glyphs: Dict[str, str], column_layouts: Dict[str, ColumnLayout], column_order: List[str]) -> str:
    trace_in()
    if not any(g.strip() for g in [glyphs['bot_left'], glyphs['bot_mid'], glyphs['bot_right']]) and not glyphs['h_bot']:
        log("No bottom border elements, returning empty string")
        trace_out()
        return ""
    segs = []
    segs.append(glyphs['bot_left'])
    for idx, c in enumerate(column_order):
        width = column_layouts[c].effective_width
        pat = glyphs['h_bot']
        if width > 0 and pat:
            reps = (width + len(pat) - 1) // len(pat)
            fill = (pat * reps)[:width]
        else:
            fill = '' if width == 0 else '-' * width if pat else ''
        segs.append(fill)
        if idx < len(column_order) - 1:
            segs.append(glyphs['bot_mid'])
    segs.append(glyphs['bot_right'])
    result = ''.join(segs)
    log(f"Bottom border built: length={len(result)}, columns={len(column_order)}")
    trace_out()
    return result
