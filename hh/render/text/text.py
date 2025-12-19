from __future__ import annotations
import json
import re
import unicodedata
from typing import Any, List, Set
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.text.color import strip_ansi, extract_last_color_code, is_reset_code, RESET_COLOR

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

try:
    import wcwidth as _wc  # type: ignore[import-untyped]
except Exception:
    _wc = None

def display_width(s: str) -> int:
    trace_in()
    
    # Filter out ANSI escape sequences for width calculation
    filtered_s = strip_ansi(s)
    #debug(f"Original string length: {len(s)}, filtered length: {len(filtered_s)}")
    
    KNOWN_SINGLE_WIDE = {
        '┌', '┐', '└', '┘',
        '├', '┤', '┬', '┴',
        '│', '─', '┼',
        '╔', '╗', '╚', '╝',
        '╠', '╣', '╦', '╩',
        '║', '═', '╬',
        '┏', '┓', '┗', '┛',
        '┣', '┫', '┳', '┻',
        '┃', '━', '╋',
        '╒', '╓', '╕', '╖',
        '╘', '╙', '╛', '╜',
        '╞', '╟', '╡', '╢',
        '╪', '╫', '╥', '╨',
        '+', '-', '|',
        '·', '•', '◦', '▪', '▫', 
    }
    KNOWN_DOUBLE_WIDE: Set[str] = set()
    if _wc is not None:
        try:
            w = _wc.wcswidth(filtered_s)
            if w >= 0:
                debug(f"wcwidth calculated display width: {w} for filtered string length {len(filtered_s)}")
                trace_out()
                return w
        except Exception as e:
            log(f"wcwidth failed: {e}, falling back to manual calculation")
    total = 0
    for i, ch in enumerate(filtered_s):
        # Check if this is a combining character that should be skipped
        if i > 0 and unicodedata.category(ch) in ('Mn', 'Me', 'Mc'):
            continue  # Skip combining marks, they're part of the previous character
        
        if ch in KNOWN_SINGLE_WIDE:
            total += 1
        elif ch in KNOWN_DOUBLE_WIDE:
            total += 2
        else:
            cat = unicodedata.category(ch)
            eaw = unicodedata.east_asian_width(ch)
            if eaw in ('W', 'F'):
                total += 2
            else:
                total += 1
    log(f"Manual calculation: display width {total} for filtered string length {len(filtered_s)}")
    trace_out()
    return total

def wrap(text: str, width: int) -> List[str]:
    trace_in()
    if width <= 0 or not text:
        result = text.split('\n') if text else ['']
        log(f"Invalid width or empty text: width={width}, returning {len(result)} lines")
        trace_out()
        return result
    
    def cut_prefix_dw(s: str, maxw: int) -> tuple[str, str]:
        if maxw <= 0:
            return '', s
        out: List[str] = []
        w = 0
        i = 0
        while i < len(s):
            ch = s[i]
            cw = display_width(ch)
            if w + cw > maxw:
                break
            out.append(ch)
            w += cw
            i += 1
        return ''.join(out), s[i:]
    
    
    leading_ws = ''
    for i, char in enumerate(text):
        if char.isspace():
            leading_ws += char
        else:
            break
    content = text[len(leading_ws):]
    content = content.rstrip()
    tokens = re.findall(r"\S+\s*", content)
    if not tokens:
        tokens = [content]
    lines: List[str] = []
    current = ''
    cur_w = 0
    current_color = ""
    saved_color = ""  # Track color state across line breaks
    
    def flush_current() -> None:
        nonlocal current, cur_w, current_color, saved_color
        if current:
            # Close any active color before line break
            if current_color:
                current += RESET_COLOR
            lines.append(current.rstrip())
            # Save the current color for the next line
            saved_color = current_color
            current = ''
            cur_w = 0
            # Don't reset current_color here - keep it for tracking
    
    def start_new_line() -> None:
        nonlocal current, current_color
        # Reapply the color that was active before the break
        if saved_color:
            current = saved_color
            current_color = saved_color
    
    for token in tokens:
        if not token:
            continue
        match = re.match(r"(?P<word>\S+)(?P<space>\s*)", token)
        if not match:
            continue
        word_part = match.group('word')
        space_part = match.group('space')
        
        # Track color changes within the word
        word_color = extract_last_color_code(word_part)
        if word_color:
            current_color = word_color
        
        word_width = display_width(word_part)
        if word_width > width:
            flush_current()
            rem_word = word_part
            while display_width(rem_word) > width:
                if width <= 1:
                    prefix, rem_word = cut_prefix_dw(rem_word, width)
                    if prefix:
                        # Extract color from prefix and track it
                        prefix_color = extract_last_color_code(prefix)
                        if prefix_color:
                            current_color = prefix_color
                        lines.append(prefix)
                    else:
                        break
                else:
                    prefix, rem_word = cut_prefix_dw(rem_word, width - 1)
                    if prefix:
                        # Extract color from prefix and track it
                        prefix_color = extract_last_color_code(prefix)
                        if prefix_color:
                            current_color = prefix_color
                        lines.append(prefix + '-')
                    else:
                        break
            word_part = rem_word
            word_width = display_width(word_part)
            # Extract color from remaining word part
            word_color = extract_last_color_code(word_part)
            if word_color:
                current_color = word_color
        
        if word_part:
            if cur_w and cur_w + word_width > width:
                flush_current()
                start_new_line()
            current += word_part
            cur_w += word_width
        
        if space_part:
            space_remaining = space_part
            while space_remaining:
                available = width - cur_w
                if available <= 0:
                    flush_current()
                    start_new_line()
                    available = width
                piece, remainder = cut_prefix_dw(space_remaining, available)
                if piece:
                    current += piece
                    cur_w += display_width(piece)
                space_remaining = remainder
                if space_remaining and cur_w:
                    flush_current()
                    start_new_line()
    
    flush_current()
    if not lines:
        result = [leading_ws] if leading_ws else ['']
        log(f"No lines generated, returning single line with leading whitespace: '{leading_ws}'")
        trace_out()
        return result
    result = [leading_ws + line for line in lines]
    log(f"Text wrapping completed: {len(result)} lines generated for width {width}")
    trace_out()
    return result

def wrap_simple(text: str, width: int, indent: str = '', pad_all_lines: bool = False, first_line_extra_indent: str = '') -> List[str]:
    trace_in()
    if width <= 0 or not text:
        parts = text.split('\n') if text else ['']
        if indent and pad_all_lines:
            result = [indent + p for p in parts]
            log(f"Invalid width, returning {len(result)} lines with indent")
            trace_out()
            return result
        if first_line_extra_indent:
            if parts:
                parts[0] = first_line_extra_indent + parts[0]
        log(f"Invalid width, returning {len(parts)} lines")
        trace_out()
        return parts
    words = text.split()
    log(f"Processing {len(words)} words for simple wrapping with width {width}")
    lines: List[str] = []
    current = ''
    for w in words:
        sep = '' if not current else ' '
        if len(current) + len(sep) + len(w) <= width:
            current = current + sep + w
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    log(f"Generated {len(lines)} lines from word wrapping")
    shaped: List[str] = []
    for i, ln in enumerate(lines):
        if i == 0 and first_line_extra_indent:
            shaped.append(first_line_extra_indent + ln.ljust(width) if pad_all_lines else first_line_extra_indent + ln)
        else:
            if pad_all_lines:
                shaped.append(indent + ln.ljust(width))
            else:
                shaped.append(indent + ln)
    log(f"Simple wrapping completed: {len(shaped)} final lines with indent='{indent}', pad_all={pad_all_lines}")
    trace_out()
    return shaped

def ellipsize(text: str, width: int, glyph: str = '…') -> str:
    trace_in()
    if width <= 0:
        log("Invalid width for ellipsize, returning empty string")
        trace_out()
        return ''
    text_width = display_width(text)
    if text_width <= width:
        log(f"Text fits in width: {text_width} <= {width}")
        trace_out()
        return text
    gw = display_width(glyph)
    core = slice(text, max(0, width - gw))
    result = core + glyph
    log(f"Text ellipsized: {text_width} -> {display_width(result)} chars with glyph '{glyph}'")
    trace_out()
    return result

def ellipsize_simple(text: str, width: int, glyph: str = '…') -> str:
    trace_in()
    if width <= 0:
        log("Invalid width for ellipsize_simple, returning original text")
        trace_out()
        return text
    if len(text) <= width:
        log(f"Text fits in width: {len(text)} <= {width}")
        trace_out()
        return text
    if width <= len(glyph):
        result = glyph[:width]
        log(f"Width too small for glyph, returning truncated glyph: {len(result)} chars")
        trace_out()
        return result
    result = text[: width - len(glyph)] + glyph
    log(f"Text ellipsized: {len(text)} -> {len(result)} chars with glyph '{glyph}'")
    trace_out()
    return result

def pad(text: str, target: int) -> str:
    trace_in()
    current_width = display_width(text)
    if current_width >= target:
        log(f"Text already meets target width: {current_width} >= {target}")
        trace_out()
        return text
    while display_width(text) < target:
        text += ' '
    final_width = display_width(text)
    log(f"Text padded: {current_width} -> {final_width} chars")
    trace_out()
    return text

def pad_simple(text: str, target: int) -> str:
    trace_in()
    if len(text) >= target:
        log(f"Text already meets target length: {len(text)} >= {target}")
        trace_out()
        return text
    while len(text) < target:
        text += ' '
    log(f"Text padded: {len(text) - (target - len(text))} -> {len(text)} chars")
    trace_out()
    return text

def slice(text: str, maxw: int) -> str:
    trace_in()
    if maxw <= 0:
        log("Invalid max width for slice, returning empty string")
        trace_out()
        return ''
    out: List[str] = []
    w = 0
    for ch in text:
        cw = display_width(ch)
        if w + cw > maxw:
            break
        out.append(ch)
        w += cw
    result = ''.join(out)
    log(f"Text sliced: {len(text)} -> {len(result)} chars, width {display_width(text)} -> {display_width(result)}")
    trace_out()
    return result

def slice_simple(text: str, maxw: int) -> str:
    trace_in()
    if maxw <= 0:
        log("Invalid max width for slice_simple, returning empty string")
        trace_out()
        return ''
    result = text[:maxw]
    log(f"Text sliced: {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def pad_left(text: str, width: int, char: str = ' ') -> str:
    trace_in()
    current_width = display_width(text)
    if current_width >= width:
        log(f"Text already meets target width: {current_width} >= {width}")
        trace_out()
        return text
    padding_needed = width - current_width
    result = (char * padding_needed) + text
    log(f"Text left-padded: {current_width} -> {display_width(result)} chars with '{char}'")
    trace_out()
    return result

def pad_left_simple(text: str, width: int, char: str = ' ') -> str:
    trace_in()
    if len(text) >= width:
        log(f"Text already meets target length: {len(text)} >= {width}")
        trace_out()
        return text
    result = text.rjust(width, char)
    log(f"Text left-padded: {len(text)} -> {len(result)} chars with '{char}'")
    trace_out()
    return result

def pad_right(text: str, width: int, char: str = ' ') -> str:
    trace_in()
    current_width = display_width(text)
    if current_width >= width:
        log(f"Text already meets target width: {current_width} >= {width}")
        trace_out()
        return text
    padding_needed = width - current_width
    result = text + (char * padding_needed)
    log(f"Text right-padded: {current_width} -> {display_width(result)} chars with '{char}'")
    trace_out()
    return result

def pad_right_simple(text: str, width: int, char: str = ' ') -> str:
    trace_in()
    if len(text) >= width:
        log(f"Text already meets target length: {len(text)} >= {width}")
        trace_out()
        return text
    result = text.ljust(width, char)
    log(f"Text right-padded: {len(text)} -> {len(result)} chars with '{char}'")
    trace_out()
    return result

def pad_center(text: str, width: int, char: str = ' ') -> str:
    trace_in()
    current_width = display_width(text)
    if current_width >= width:
        log(f"Text already meets target width: {current_width} >= {width}")
        trace_out()
        return text
    diff = width - current_width
    left = diff // 2
    right = diff - left
    result = (char * left) + text + (char * right)
    log(f"Text center-padded: {current_width} -> {display_width(result)} chars with '{char}' (left={left}, right={right})")
    trace_out()
    return result

def pad_center_simple(text: str, width: int, char: str = ' ') -> str:
    trace_in()
    if len(text) >= width:
        log(f"Text already meets target length: {len(text)} >= {width}")
        trace_out()
        return text
    result = text.center(width, char)
    log(f"Text center-padded: {len(text)} -> {len(result)} chars with '{char}'")
    trace_out()
    return result

def repeat_pattern(pattern: str, width: int) -> str:
    trace_in()
    if not pattern or width <= 0:
        log("Invalid pattern or width for repeat_pattern, returning empty string")
        trace_out()
        return ''
    pattern_width = display_width(pattern)
    if pattern_width == 0:
        log("Pattern has zero display width, returning empty string")
        trace_out()
        return ''
    full_repeats = width // pattern_width
    remainder = width % pattern_width
    result = pattern * full_repeats
    if remainder > 0:
        result += slice(pattern, remainder)
    log(f"Pattern repeated: '{pattern}' ({pattern_width} width) -> {display_width(result)} total width")
    trace_out()
    return result

def repeat_pattern_simple(pattern: str, width: int) -> str:
    trace_in()
    if not pattern or width <= 0:
        log("Invalid pattern or width for repeat_pattern_simple, returning empty string")
        trace_out()
        return ''
    full_repeats = width // len(pattern)
    remainder = width % len(pattern)
    result = pattern * full_repeats
    if remainder > 0:
        result += pattern[:remainder]
    log(f"Pattern repeated: '{pattern}' ({len(pattern)} length) -> {len(result)} total length")
    trace_out()
    return result

def clean_whitespace(text: str) -> str:
    trace_in()
    import re
    result = re.sub(r'\s+', ' ', text.strip())
    log(f"Whitespace cleaned: {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def clean_whitespace_simple(text: str) -> str:
    trace_in()
    result = ' '.join(text.split())
    log(f"Whitespace cleaned: {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def strip_ansi_simple(text: str) -> str:
    trace_in()
    result = strip_ansi(text)
    log(f"ANSI codes stripped (simple): {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def normalize_line_endings(text: str) -> str:
    trace_in()
    result = text.replace('\r\n', '\n').replace('\r', '\n')
    log(f"Line endings normalized: {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def normalize_line_endings_simple(text: str) -> str:
    trace_in()
    result = normalize_line_endings(text)
    log(f"Line endings normalized (simple): {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def indent(text: str, prefix: str = '  ', skip_first: bool = False) -> str:
    trace_in()
    lines = text.splitlines(True)
    if not lines:
        log("No lines to indent, returning original text")
        trace_out()
        return text
    if skip_first:
        result = lines[0] + ''.join(prefix + line for line in lines[1:])
        log(f"Text indented (skip first): {len(lines)} lines with prefix '{prefix}'")
    else:
        result = ''.join(prefix + line for line in lines)
        log(f"Text indented: {len(lines)} lines with prefix '{prefix}'")
    trace_out()
    return result

def indent_simple(text: str, prefix: str = '  ', skip_first: bool = False) -> str:
    trace_in()
    result = indent(text, prefix, skip_first)
    log(f"Text indented (simple): {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def dedent(text: str) -> str:
    trace_in()
    import textwrap
    result = textwrap.dedent(text)
    log(f"Text dedented: {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def dedent_simple(text: str) -> str:
    trace_in()
    result = dedent(text)
    log(f"Text dedented (simple): {len(text)} -> {len(result)} chars")
    trace_out()
    return result

def justify(text: str, width: int) -> str:
    trace_in()
    words = text.split()
    if len(words) <= 1:
        log("Not enough words to justify, returning original text")
        trace_out()
        return text
    total_width = sum(display_width(word) for word in words)
    if total_width >= width:
        log(f"Text already meets target width: {total_width} >= {width}")
        trace_out()
        return text
    spaces_needed = width - total_width
    gaps = len(words) - 1
    if gaps == 0:
        log("No gaps between words, returning original text")
        trace_out()
        return text
    base_spaces = spaces_needed // gaps
    extra_spaces = spaces_needed % gaps
    result = words[0]
    for i, word in enumerate(words[1:], 1):
        spaces = base_spaces + (1 if i <= extra_spaces else 0)
        result += ' ' * spaces + word
    log(f"Text justified: {total_width} -> {display_width(result)} width with {gaps} gaps")
    trace_out()
    return result

def justify_simple(text: str, width: int) -> str:
    trace_in()
    words = text.split()
    if len(words) <= 1:
        log("Not enough words to justify, returning original text")
        trace_out()
        return text
    total_width = sum(len(word) for word in words)
    if total_width >= width:
        log(f"Text already meets target width: {total_width} >= {width}")
        trace_out()
        return text
    spaces_needed = width - total_width
    gaps = len(words) - 1
    if gaps == 0:
        log("No gaps between words, returning original text")
        trace_out()
        return text
    base_spaces = spaces_needed // gaps
    extra_spaces = spaces_needed % gaps
    result = words[0]
    for i, word in enumerate(words[1:], 1):
        spaces = base_spaces + (1 if i <= extra_spaces else 0)
        result += ' ' * spaces + word
    log(f"Text justified (simple): {total_width} -> {len(result)} width with {gaps} gaps")
    trace_out()
    return result

def to_title_case(text: str) -> str:
    trace_in()
    result = text.title()
    log(f"Text converted to title case: '{text}' -> '{result}'")
    trace_out()
    return result

def to_title_case_simple(text: str) -> str:
    trace_in()
    result = to_title_case(text)
    log(f"Text converted to title case (simple): '{text}' -> '{result}'")
    trace_out()
    return result

def to_snake_case(text: str) -> str:
    trace_in()
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    log(f"Text converted to snake case: '{text}' -> '{result}'")
    trace_out()
    return result

def to_snake_case_simple(text: str) -> str:
    trace_in()
    result = to_snake_case(text)
    log(f"Text converted to snake case (simple): '{text}' -> '{result}'")
    trace_out()
    return result

def to_camel_case(text: str) -> str:
    trace_in()
    import re
    components = re.split(r'[-_\s]+', text)
    result = components[0].lower() + ''.join(word.capitalize() for word in components[1:])
    log(f"Text converted to camel case: '{text}' -> '{result}' ({len(components)} components)")
    trace_out()
    return result

def to_camel_case_simple(text: str) -> str:
    trace_in()
    result = to_camel_case(text)
    log(f"Text converted to camel case (simple): '{text}' -> '{result}'")
    trace_out()
    return result

def to_kebab_case(text: str) -> str:
    trace_in()
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', text)
    result = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()
    log(f"Text converted to kebab case: '{text}' -> '{result}'")
    trace_out()
    return result

def to_kebab_case_simple(text: str) -> str:
    trace_in()
    result = to_kebab_case(text)
    log(f"Text converted to kebab case (simple): '{text}' -> '{result}'")
    trace_out()
    return result

def get_max_width(table_output: str) -> int:
    trace_in()
    if not table_output:
        log("Empty table output, returning 0")
        trace_out()
        return 0
    try:
        lines = table_output.split('\n')
        max_width = 0
        non_empty_lines = 0
        for line in lines:
            if line.strip():  # Skip empty lines
                non_empty_lines += 1
                line_width = display_width(line)
                if line_width > max_width:
                    max_width = line_width
        log(f"Calculated max width: {max_width} from {non_empty_lines} non-empty lines out of {len(lines)} total")
        trace_out()
        return max_width
    except Exception as e:
        warn(f"Error calculating max width: {e}")
        log("Returning 0 due to error")
        trace_out()
        return 0
