from __future__ import annotations
import re
from typing import Dict, List, Optional

RESET_COLOR = "\033[0m"

COLORS: Dict[str, str] = {
    'red': "\033[38;5;196m",
    'orange': "\033[38;5;208m",
    'yellow': "\033[38;5;226m",
    'green': "\033[38;5;46m",
    'cyan': "\033[38;5;51m",
    'blue': "\033[38;5;21m",
    'magenta': "\033[38;5;201m",
    'gold': "\033[38;5;214m",
    'white': "\033[38;5;15m",
    'brown': "\033[38;5;130m",
    'pink': "\033[38;5;218m",
    'pastel_yellow': "\033[38;5;229m",
    'pastel_cyan': "\033[38;5;195m",
    'pastel_pink': "\033[38;5;225m",
    'pastel_green': "\033[38;5;194m",
    'pastel_blue': "\033[38;5;159m",
    'pastel_purple': "\033[38;5;183m",
    'pastel_orange': "\033[38;5;223m",
    'pastel_red': "\033[38;5;224m",
    'pastel_lavender': "\033[38;5;219m",
    'pastel_peach': "\033[38;5;209m",
    'pastel_mint': "\033[38;5;122m",
    'pastel_lilac': "\033[38;5;141m",
    'pastel_sky': "\033[38;5;117m",
    'pastel_rose': "\033[38;5;224m",
    'pastel_aqua': "\033[38;5;146m",
    'pastel_coral': "\033[38;5;216m",
    'pastel_lime': "\033[38;5;154m",
    'pastel_violet': "\033[38;5;149m",
}

COLOR_NAMES = list(COLORS.keys())

class ColorManager:
    """Manages automatic color assignment for strings using round-robin color indexing."""
    
    def __init__(self) -> None:
        self._pools: Dict[str, Dict[str, int]] = {}
        self._indices: Dict[str, int] = {}
    
    def get_color_index(self, item: str, pool: str = "default") -> int:
        """Get the color index for an item in a specific pool. Creates a new mapping if needed."""
        if pool not in self._pools:
            self._pools[pool] = {}
            self._indices[pool] = 0
        
        if item not in self._pools[pool]:
            self._pools[pool][item] = self._indices[pool]
            self._indices[pool] = (self._indices[pool] + 1) % len(COLOR_NAMES)
        return self._pools[pool][item]
    
    def get_color_code(self, item: str, pool: str = "default") -> str:
        """Get the raw color code for an item in a specific pool."""
        color_index = self.get_color_index(item, pool)
        color_name = COLOR_NAMES[color_index]
        return COLORS[color_name]
    
    def get_colored(self, item: str, text: Optional[str] = None, condition: bool = True, pool: str = "default") -> str:
        """Apply rainbow color to text based on item name. Returns original if condition is False."""
        display_text = text if text is not None else item
        if not display_text or not condition:
            return display_text
        color_code = self.get_color_code(item, pool)
        return f"{color_code}{display_text}{RESET_COLOR}"
    
    def clear(self, pool: Optional[str] = None) -> None:
        """Clear color mappings. If pool is None, clears all pools."""
        if pool is None:
            self._pools.clear()
            self._indices.clear()
        else:
            self._pools.pop(pool, None)
            self._indices.pop(pool, None)

def get_color(color_name: str) -> str:
    """Get color code by name."""
    return COLORS.get(color_name, "")

def apply_color(text: str, color_name: str) -> str:
    """Apply a named color to text."""
    color_code = get_color(color_name)
    if not color_code or not text:
        return text
    return f"{color_code}{text}{RESET_COLOR}"

def apply_color_to_multiline(text: str, color_code: str) -> str:
    """Apply color to text that may contain line breaks, injecting resets/restarts at line boundaries."""
    if '\n' not in text:
        return f"{color_code}{text}{RESET_COLOR}"
    
    lines = text.split('\n')
    result_parts = []
    
    for i, line in enumerate(lines):
        if i == 0:
            result_parts.append(f"{color_code}{line}")
        else:
            result_parts.append(f"{color_code}{line}")
        
        if i < len(lines) - 1:
            result_parts.append(f"{RESET_COLOR}\n")
    
    result_parts.append(RESET_COLOR)
    return ''.join(result_parts)

def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def has_color_codes(text: str) -> bool:
    """Check if text contains ANSI color codes."""
    return bool(re.search(r'\x1b\[[0-9;]*m', text))

def apply_color_code(text: str, color_code: str) -> str:
    """Apply a raw color code to text."""
    if not color_code or not text:
        return text
    return f"{color_code}{text}{RESET_COLOR}"

def is_reset_code(color_code: str) -> bool:
    """Check if a color code is a reset code."""
    return color_code == RESET_COLOR

def extract_last_color_code(text: str) -> str:
    """Extract the last active color code from text, ignoring reset codes."""
    # Pattern to find ANSI escape codes
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    color_matches = list(ansi_pattern.finditer(text))
    
    if not color_matches:
        return ""
    
    # Find the last non-reset color code
    last_color = ""
    for match in reversed(color_matches):
        color_code = match.group(0)
        if is_reset_code(color_code):
            break  # Stop at reset, don't look further back
        else:
            last_color = color_code
            break
    
    return last_color

__all__ = [
    'RESET_COLOR',
    'COLORS',
    'COLOR_NAMES',
    'ColorManager',
    'get_color',
    'apply_color',
    'apply_color_to_multiline',
    'strip_ansi',
    'has_color_codes',
    'apply_color_code',
    'is_reset_code',
    'extract_last_color_code',
]
