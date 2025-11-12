from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Union
from hh.render.text.text import display_width
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

BlockInput = Union[str, Sequence[str]]

def _split_lines(block: BlockInput) -> List[str]:
    if isinstance(block, str):
        return block.splitlines() or ['']
    lines = list(block)
    return lines or ['']

def _pad_line(line: str, width: int) -> str:
    missing = width - display_width(line)
    if missing <= 0:
        return line
    return line + (' ' * missing)

def _empty_line(width: int) -> str:
    return ' ' * max(0, width)

@dataclass
class QuiltBlock:
    lines: List[str]
    width: int
    height: int

    @classmethod
    def from_input(cls, block: BlockInput, pad_horizontal: int = 0, pad_vertical: int = 0) -> 'QuiltBlock':
        trace_in()
        raw_lines = _split_lines(block)
        width = max((display_width(line) for line in raw_lines), default=0)
        normalized = [_pad_line(line, width) for line in raw_lines]
        if pad_horizontal:
            normalized = [
                (' ' * pad_horizontal) + line + (' ' * pad_horizontal)
                for line in normalized
            ]
            width += pad_horizontal * 2
        if pad_vertical:
            blank = _empty_line(width)
            normalized = [blank] * pad_vertical + normalized + [blank] * pad_vertical
        height = len(normalized)
        log(f"Created QuiltBlock: {width}x{height} with {len(raw_lines)} original lines")
        trace_out()
        return cls(normalized, width, height)

    def expand_height(self, target: int, valign: str) -> 'QuiltBlock':
        if target <= self.height:
            return self
        pad_needed = target - self.height
        if valign == 'bottom':
            top = pad_needed
        elif valign == 'middle' or valign == 'center':
            top = pad_needed // 2
        else:
            top = 0
        bottom = pad_needed - top
        blank = _empty_line(self.width)
        lines = [blank] * top + self.lines + [blank] * bottom
        return QuiltBlock(lines, self.width, target)

    def expand_width(self, target: int, align: str) -> 'QuiltBlock':
        if target <= self.width:
            return self
        pad_needed = target - self.width
        if align == 'right':
            left = pad_needed
        elif align in ('middle', 'center'):
            left = pad_needed // 2
        else:
            left = 0
        right = pad_needed - left
        lines = [
            (' ' * left) + line + (' ' * right)
            for line in self.lines
        ]
        return QuiltBlock(lines, target, self.height)

def _prepare_blocks(blocks: Iterable[BlockInput], pad_horizontal: int, pad_vertical: int) -> List[QuiltBlock]:
    trace_in()
    result = [QuiltBlock.from_input(block, pad_horizontal, pad_vertical) for block in blocks]
    log(f"Prepared {len(result)} blocks with padding h={pad_horizontal}, v={pad_vertical}")
    trace_out()
    return result

def _render_row(blocks: Sequence[QuiltBlock], gap_x: int) -> List[str]:
    if not blocks:
        return []
    gap = ' ' * max(0, gap_x)
    row_height = blocks[0].height
    lines: List[str] = []
    for i in range(row_height):
        segments = []
        for idx, block in enumerate(blocks):
            segments.append(block.lines[i])
            if idx < len(blocks) - 1:
                segments.append(gap)
        lines.append(''.join(segments))
    return lines

def quilt_flow(
    blocks: Iterable[BlockInput],
    max_width: int,
    *,
    gap_x: int = 2,
    gap_y: int = 1,
    align: str = 'left',
    valign: str = 'top',
    pad_horizontal: int = 0,
    pad_vertical: int = 0,
) -> str:
    trace_in()
    prepared = _prepare_blocks(blocks, pad_horizontal, pad_vertical)
    log(f"Prepared {len(prepared)} blocks for flow layout with max_width={max_width}")
    rows: List[List[QuiltBlock]] = []
    current_row: List[QuiltBlock] = []
    current_width = 0
    for block in prepared:
        block_width = block.width
        projected = block_width if not current_row else current_width + gap_x + block_width
        if current_row and projected > max_width:
            rows.append(current_row)
            current_row = []
            current_width = 0
        if current_row:
            current_width += gap_x
        current_row.append(block)
        current_width += block_width
    if current_row:
        rows.append(current_row)
    log(f"Created {len(rows)} rows for flow layout")
    rendered_rows: List[str] = []
    gap_line = _empty_line(max_width)
    for row_idx, row_blocks in enumerate(rows):
        row_height = max(block.height for block in row_blocks)
        aligned_blocks = [block.expand_height(row_height, valign) for block in row_blocks]
        row_lines = _render_row(aligned_blocks, gap_x)
        aligned_row_lines = []
        for line in row_lines:
            width = display_width(line)
            if width >= max_width:
                aligned_row_lines.append(line)
                continue
            padding = max_width - width
            if align == 'right':
                aligned_line = (' ' * padding) + line
            elif align in ('middle', 'center'):
                left = padding // 2
                right = padding - left
                aligned_line = (' ' * left) + line + (' ' * right)
            else:
                aligned_line = line + (' ' * padding)
            aligned_row_lines.append(aligned_line)
        rendered_rows.extend(aligned_row_lines)
        if gap_y and row_idx < len(rows) - 1:
            rendered_rows.extend([gap_line] * gap_y)
    result = '\n'.join(rendered_rows)
    log(f"Flow layout completed: {len(rendered_rows)} lines generated")
    trace_out()
    return result

def quilt_grid(
    blocks: Iterable[BlockInput],
    columns: int,
    *,
    gap_x: int = 2,
    gap_y: int = 1,
    align: str = 'left',
    valign: str = 'top',
    pad_horizontal: int = 0,
    pad_vertical: int = 0,
) -> str:
    trace_in()
    if columns <= 0:
        warn(f"Invalid column count: {columns}, must be positive")
        trace_out()
        raise ValueError('columns must be positive')
    prepared = _prepare_blocks(blocks, pad_horizontal, pad_vertical)
    log(f"Prepared {len(prepared)} blocks for grid layout with {columns} columns")
    if not prepared:
        log("No blocks to process, returning empty string")
        trace_out()
        return ''
    grid: List[List[QuiltBlock]] = []
    row: List[QuiltBlock] = []
    for block in prepared:
        row.append(block)
        if len(row) == columns:
            grid.append(row)
            row = []
    if row:
        log(f"Padding final row with {columns - len(row)} empty blocks")
        empty = QuiltBlock([''], 1, 1)
        while len(row) < columns:
            row.append(empty)
        grid.append(row)
    log(f"Created grid with {len(grid)} rows")
    col_widths = [0] * columns
    for col in range(columns):
        col_widths[col] = max(row[col].width for row in grid)
    row_heights = [0] * len(grid)
    for r_idx, row_blocks in enumerate(grid):
        row_heights[r_idx] = max(block.height for block in row_blocks)
    log(f"Calculated column widths: {col_widths}, row heights: {row_heights}")
    normalized_rows: List[List[QuiltBlock]] = []
    for r_idx, row_blocks in enumerate(grid):
        normalized_row: List[QuiltBlock] = []
        for c_idx, block in enumerate(row_blocks):
            widened = block.expand_width(col_widths[c_idx], align)
            expanded = widened.expand_height(row_heights[r_idx], valign)
            normalized_row.append(expanded)
        normalized_rows.append(normalized_row)
    rendered_lines: List[str] = []
    gap_columns = ' ' * gap_x
    for r_idx, row_blocks in enumerate(normalized_rows):
        row_lines = _render_row(row_blocks, gap_x)
        rendered_lines.extend(row_lines)
        if gap_y and r_idx < len(normalized_rows) - 1:
            blank_width = sum(col_widths) + gap_x * (columns - 1)
            rendered_lines.extend([_empty_line(blank_width)] * gap_y)
    result = '\n'.join(rendered_lines)
    log(f"Grid layout completed: {len(rendered_lines)} lines generated")
    trace_out()
    return result

def quilt_columns(
    column_groups: Sequence[Iterable[BlockInput]],
    *,
    gap_x: int = 4,
    gap_y: int = 1,
    align: str = 'left',
    valign: str = 'top',
    pad_horizontal: int = 0,
    pad_vertical: int = 0,
) -> str:
    trace_in()
    columns: List[List[QuiltBlock]] = []
    for group in column_groups:
        blocks = _prepare_blocks(group, pad_horizontal, pad_vertical)
        if not blocks:
            log("Empty column group, adding empty block")
            blocks = [QuiltBlock([''], 1, 1)]
        columns.append(blocks)
    log(f"Prepared {len(columns)} column groups for column layout")
    if not columns:
        log("No column groups to process, returning empty string")
        trace_out()
        return ''
    column_blocks: List[QuiltBlock] = []
    for blocks in columns:
        column_lines: List[str] = []
        max_width = max(block.width for block in blocks)
        for idx, block in enumerate(blocks):
            widened = block.expand_width(max_width, align)
            column_lines.extend(widened.lines)
            if gap_y and idx < len(blocks) - 1:
                column_lines.extend([_empty_line(max_width)] * gap_y)
        column_blocks.append(QuiltBlock(column_lines, max_width, len(column_lines)))
    max_height = max(block.height for block in column_blocks)
    log(f"Calculated max height: {max_height} for {len(column_blocks)} columns")
    aligned_columns = [block.expand_height(max_height, valign) for block in column_blocks]
    final_lines = _render_row(aligned_columns, gap_x)
    result = '\n'.join(final_lines)
    log(f"Column layout completed: {len(final_lines)} lines generated")
    trace_out()
    return result

__all__ = ['quilt_flow', 'quilt_grid', 'quilt_columns']
