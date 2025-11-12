from pathlib import Path
from typing import Dict, Any, List
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

def index_sections(md_file: Path, sections: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    trace_in()
    title = md_file.stem
    directory_name = md_file.parent.name
    is_special = title == directory_name
    log(f"Indexing sections for file: {md_file}")
    log(f"Title: {title}, Directory: {directory_name}, Special: {is_special}")
    log(f"Processing {len(sections)} sections")
    entry = {
        'file': str(md_file),
        'sections': sections,
        'meta': {
            'type': 'special' if is_special else 'regular'
        }
    }
    log(f"Created index entry with {len(sections)} sections")
    trace_out()
    return entry

def get_content_from_file(filename: str, range_info: Dict[str, int]) -> str:
    trace_in()
    log(f"Reading content from file: {filename}")
    log(f"Range: {range_info['start']}-{range_info['end']}")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        log(f"Read {len(lines)} lines from file")
        start = range_info['start']
        end = range_info['end']
        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        content = ''.join(lines[start_idx:end_idx]).strip()
        log(f"Extracted content: {len(content)} characters from lines {start_idx+1}-{end_idx}")
        trace_out()
        return content
    except Exception as e:
        warn(f"Error reading file {filename}: {e}")
        trace_out()
        return ""

def find_sibling_files(file_path: str) -> List[str]:
    trace_in()
    directory = Path(file_path).parent
    log(f"Looking for sibling files in directory: {directory}")
    sibling_files = []
    for md_file in directory.glob("*.md"):
        if md_file.name != Path(file_path).name:
            sibling_files.append(str(md_file))
            log(f"Found sibling file: {md_file.name}")
    log(f"Found {len(sibling_files)} sibling files")
    trace_out()
    return sibling_files

def find_child_directories(file_path: str) -> List[str]:
    trace_in()
    parent_dir = Path(file_path).parent
    log(f"Looking for child directories in: {parent_dir}")
    child_dirs = []
    for child_dir in parent_dir.iterdir():
        if child_dir.is_dir():
            md_file = child_dir / f"{child_dir.name}.md"
            if md_file.exists():
                child_dirs.append(child_dir.name)
                log(f"Found child directory with .md file: {child_dir.name}")
            else:
                log(f"Skipped child directory (no .md file): {child_dir.name}")
    log(f"Found {len(child_dirs)} child directories with .md files")
    trace_out()
    return child_dirs
