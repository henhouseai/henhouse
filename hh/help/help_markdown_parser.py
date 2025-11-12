from pathlib import Path
from typing import Dict
from hh.help.help_utils import map_header_to_bucket
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

def parse_markdown_file(md_file: Path) -> Dict[str, Dict[str, int]]:
    trace_in()
    log(f"Parsing markdown file: {md_file}")
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        log(f"Read {len(content)} characters from file")
        sections = parse_content(content)
        if not sections:
            warn(f"No sections found in {md_file}")
            trace_out()
            return {}
        log(f"Found {len(sections)} sections in file")
        trace_out()
        return sections
    except Exception as e:
        warn(f"Error parsing {md_file}: {e}")
        trace_out()
        return {}

def parse_content(content: str) -> Dict[str, Dict[str, int]]:
    trace_in()
    sections: Dict[str, Dict[str, int]] = {}
    lines = content.split('\n')
    current_main = None
    current_sub = None
    log(f"Processing {len(lines)} lines of content")
    
    for idx, line in enumerate(lines):
        if line.startswith('# '):
            if current_main and current_sub:
                section_key = f"{current_main}.{current_sub}"
                if section_key in sections:
                    sections[section_key]['end'] = idx
                    log(f"Closed section: {section_key}")
            current_main = line[2:].strip()
            current_sub = None
            log(f"Started main section: {current_main}")
        elif line.startswith('## '):
            if current_main and current_sub:
                section_key = f"{current_main}.{current_sub}"
                if section_key in sections:
                    sections[section_key]['end'] = idx
                    log(f"Closed subsection: {section_key}")
            if current_main:
                header_text = line[3:].strip()
                content_bucket = map_header_to_bucket(header_text)
                if content_bucket:
                    section_key = f"{current_main}.{content_bucket}"
                    sections[section_key] = {'start': idx + 2, 'end': len(lines)}
                    current_sub = content_bucket
                    log(f"Started subsection: {section_key}")
                else:
                    warn(f"Unrecognized header in {current_main}: {header_text}")
        elif line.strip() == '---':
            if current_main and current_sub:
                section_key = f"{current_main}.{current_sub}"
                if section_key in sections:
                    sections[section_key]['end'] = idx
                    log(f"Closed section at separator: {section_key}")
            current_sub = None
    
    log(f"Parsed {len(sections)} sections from content")
    trace_out()
    return sections
