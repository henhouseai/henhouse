import csv
from pathlib import Path
from typing import Dict, Optional
from hh.help.help_utils import get_default_paths
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

class Registry:
    def __init__(self, help_dir: Optional[Path] = None, cache_path: Optional[Path] = None):
        trace_in()
        self.help_dir, self.registry_file = get_default_paths()
        if help_dir:
            self.help_dir = help_dir
            log(f"Using custom help directory: {self.help_dir}")
        if cache_path:
            self.registry_file = cache_path
            log(f"Using custom registry file: {self.registry_file}")
        self._command_index: Dict[str, Dict] = {}
        self._loaded = False
        log(f"Registry initialized with help_dir: {self.help_dir}, registry_file: {self.registry_file}")
        trace_out()
    
    def load(self) -> bool:
        trace_in()
        log(f"Loading registry from: {self.registry_file}")
        if not self.registry_file.exists():
            log(f"Registry file not found, will rebuild: {self.registry_file}")
            trace_out()
            return False
        try:
            self._command_index.clear()
            log("Cleared existing command index")
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                row_count = 0
                for row in reader:
                    title = row['title']
                    filename = row['filename']
                    if title not in self._command_index:
                        directory_name = Path(filename).parent.name
                        is_special = title == directory_name
                        self._command_index[title] = {
                            'file': filename,
                            'sections': {},
                            'meta': {'type': 'special' if is_special else 'regular'}
                        }
                        log(f"Added topic: {title} (type: {'special' if is_special else 'regular'})")
                    section_key = f"{row['section']}.{row['sub_section']}"
                    self._command_index[title]['sections'][section_key] = {
                        'start': int(row['start']),
                        'end': int(row['end'])
                    }
                    row_count += 1
            self._loaded = True
            log(f"Successfully loaded registry with {len(self._command_index)} topics from {row_count} rows")
            trace_out()
            return True
        except Exception as e:
            warn(f"Error loading registry: {e}")
            trace_out()
            return False
    
    def save(self) -> None:
        trace_in()
        log(f"Saving registry to: {self.registry_file}")
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        log(f"Created directory: {self.registry_file.parent}")
        with open(self.registry_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(['title', 'section', 'sub_section', 'start', 'end', 'filename'])
            row_count = 0
            for title, entry in self._command_index.items():
                for section_key, range_info in entry['sections'].items():
                    section, sub_section = section_key.split('.', 1)
                    writer.writerow([
                        title,
                        section,
                        sub_section,
                        range_info['start'],
                        range_info['end'],
                        entry['file']
                    ])
                    row_count += 1
        log(f"Successfully saved registry with {len(self._command_index)} topics and {row_count} sections")
        trace_out()
    
    def rebuild(self) -> None:
        trace_in()
        log(f"Rebuilding registry from help directory: {self.help_dir}")
        self._command_index.clear()
        log("Cleared existing command index")
        from hh.help.help_markdown_parser import parse_markdown_file
        from hh.help.help_section_index import index_sections
        seen_titles = {}
        md_files = list(self.help_dir.rglob('*.md'))
        log(f"Found {len(md_files)} markdown files to process")
        for md_file in sorted(md_files):
            log(f"Processing file: {md_file}")
            sections = parse_markdown_file(md_file)
            if sections:
                title = md_file.stem
                if title in seen_titles:
                    existing_file = seen_titles[title]
                    error_msg = f"Duplicate help filename '{title}.md' found in both:\n  - {existing_file}\n  - {md_file}\nHelp filenames must be unique across all directories."
                    warn(error_msg)
                    trace_out()
                    raise ValueError(error_msg)
                seen_titles[title] = str(md_file)
                indexed = index_sections(md_file, sections)
                self._command_index[title] = indexed
                log(f"Indexed topic: {title} with {len(sections)} sections")
            else:
                log(f"No sections found in file: {md_file}")
        self.save()
        self._loaded = True
        log(f"Registry rebuild completed with {len(self._command_index)} topics")
        trace_out()
    
    def lookup(self, title: str) -> Optional[Dict]:
        trace_in()
        log(f"Looking up topic: {title}")
        result = self._command_index.get(title)
        if result:
            log(f"Found topic: {title} with {len(result.get('sections', {}))} sections")
        else:
            log(f"Topic not found: {title}")
        trace_out()
        return result
    
    def all_topics(self) -> list[str]:
        trace_in()
        topics = list(self._command_index.keys())
        log(f"Retrieved {len(topics)} topics: {', '.join(topics)}")
        trace_out()
        return topics
    
    def clear(self) -> None:
        trace_in()
        log("Clearing registry command index")
        self._command_index.clear()
        self._loaded = False
        log("Registry cleared and marked as not loaded")
        trace_out()
