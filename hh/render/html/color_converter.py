from __future__ import annotations
import re
import html
from typing import List, Tuple, Optional
from hh.render.text.color import COLORS, RESET_COLOR

# Reverse lookup: ANSI code -> color name
COLOR_CODE_TO_NAME: dict[str, str] = {code: name for name, code in COLORS.items()}

def ansi_code_to_color_name(code: str) -> Optional[str]:
    """Convert ANSI escape code to color name."""
    # Handle reset code
    if code == RESET_COLOR or code == "\033[0m":
        return None
    
    # Direct lookup
    if code in COLOR_CODE_TO_NAME:
        return COLOR_CODE_TO_NAME[code]
    
    # Parse sequence (format: \x1b[38;5;{n}m)
    match = re.match(r'\x1b\[38;5;(\d+)m', code)
    if match:
        code_num = int(match.group(1))
        # Try to find matching color by testing against known codes
        for name, known_code in COLORS.items():
            known_match = re.match(r'\x1b\[38;5;(\d+)m', known_code)
            if known_match and int(known_match.group(1)) == code_num:
                return name
    
    return None

def parse_color_segments(text: str) -> List[Tuple[str, Optional[str]]]:
    """
    Parse text with ANSI codes into segments with color information.
    Returns list of (text_segment, color_name) tuples.
    """
    if not text:
        return [("", None)]
    
    segments: List[Tuple[str, Optional[str]]] = []
    current_text = ""
    current_color: Optional[str] = None
    
    # Pattern to match ANSI codes
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    
    i = 0
    while i < len(text):
        # Try to match ANSI code at current position
        match = ansi_pattern.match(text, i)
        if match:
            # Save current segment if we have text
            if current_text:
                segments.append((current_text, current_color))
                current_text = ""
            
            # Process the ANSI code
            code = match.group(0)
            if code == RESET_COLOR or code == "\033[0m":
                current_color = None
            else:
                current_color = ansi_code_to_color_name(code)
            
            i = match.end()
        else:
            current_text += text[i]
            i += 1
    
    # Add remaining text
    if current_text:
        segments.append((current_text, current_color))
    
    # If no segments were created, return empty text segment
    if not segments:
        segments.append(("", None))
    
    return segments

def get_uniform_cell_color(cell_value: str) -> Optional[str]:
    """
    Check if entire cell content has a single color.
    Returns color name if uniform, None if mixed/no color.
    """
    segments = parse_color_segments(cell_value)
    
    if not segments:
        return None
    
    # Check if all non-empty segments have the same color
    colors = [color for text, color in segments if text.strip()]
    if not colors:
        return None
    
    first_color = colors[0]
    if all(c == first_color for c in colors):
        return first_color
    
    return None

def get_uniform_row_color(row_values: List[str]) -> Optional[str]:
    """
    Check if all cells in a row have the same color.
    Returns color name if uniform, None if mixed.
    """
    row_colors = []
    for cell_value in row_values:
        cell_color = get_uniform_cell_color(str(cell_value))
        if cell_color:
            row_colors.append(cell_color)
    
    if not row_colors:
        return None
    
    first_color = row_colors[0]
    if all(c == first_color for c in row_colors):
        return first_color
    
    return None

def convert_ansi_to_html(text: str) -> str:
    """
    Convert ANSI color codes in text to HTML <span> tags.
    Returns HTML with color spans and ANSI codes stripped.
    """
    if not text:
        return ""
    
    segments = parse_color_segments(text)
    html_parts = []
    
    for text_segment, color_name in segments:
        if not text_segment:
            continue
        
        escaped_text = html.escape(text_segment)
        
        if color_name:
            html_parts.append(f'<span class="color-{color_name}">{escaped_text}</span>')
        else:
            html_parts.append(escaped_text)
    
    return ''.join(html_parts)

