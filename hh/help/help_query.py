import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from hh.help.help_registry import Registry
from hh.help.help_section_index import get_content_from_file, find_sibling_files
from hh.help.help_utils import get_default_paths
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.cache.cache_cleanup_registry import get_deployment_paths, register_cache_cleanup
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup

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

class HelpQuery:
    def __init__(self, topic: str, section: Optional[str] = None, help_dir: Optional[Union[str, Path]] = None):
        trace_in()
        log(f"Initializing HelpQuery for topic: {topic}, section: {section}")
        self.help_dir, self.registry_file = get_default_paths()
        if help_dir:
            self.help_dir = Path(help_dir)
            self.registry_file = self.help_dir.parent / "tools" / "log" / "help_registry.tsv"
            log(f"Using custom help directory: {self.help_dir}")
        self.registry = Registry(self.help_dir, self.registry_file)
        self.topic = topic
        self.section = section
        self.sections: Dict[str, str] = {}
        self._populate_sections()
        log(f"HelpQuery initialized with {len(self.sections)} sections")
        trace_out()

    def _populate_sections(self):
        trace_in()
        self._ensure_loaded()
        if self.section:
            log(f"Populating single section: {self.section}")
            content = self.get_section(self.topic, self.section)
            self.sections[self.section] = content
            log(f"Added section content: {len(content)} characters")
        else:
            log(f"Populating all sections for topic: {self.topic}")
            main_content = self.get_section(self.topic, self.topic)
            self.sections[self.topic] = main_content
            log(f"Added main content: {len(main_content)} characters")
            entry = self.registry.lookup(self.topic)
            if entry:
                file_path = entry['file']
                is_special = entry['meta']['type'] == 'special'
                log(f"File type: {'special' if is_special else 'regular'}")
                if is_special:
                    child_descriptions = self._get_child_directories(file_path)
                    sibling_files = find_sibling_files(file_path)
                    sibling_summaries = self._get_sibling_summaries(sibling_files)
                    log(f"Found {len(child_descriptions)} child directories, {len(sibling_files)} sibling files")
                    for child_name, desc_content in child_descriptions.items():
                        self.sections[f"child_{child_name}"] = desc_content
                        log(f"Added child directory: {child_name}")
                    for sibling_topic, summary_content in sibling_summaries.items():
                        self.sections[f"file_{sibling_topic}"] = summary_content
                        log(f"Added sibling file: {sibling_topic}")
                else:
                    for topic_name, topic_entry in self.registry._command_index.items():
                        if topic_entry['file'] == file_path:
                            unique_sections = set()
                            for section_key, range_info in topic_entry['sections'].items():
                                section, sub_section = section_key.split('.', 1)
                                if section != self.topic:
                                    unique_sections.add(section)
                            log(f"Found {len(unique_sections)} unique sections")
                            for section in unique_sections:
                                content = self.get_sub_section(topic_name, section, "description")
                                self.sections[section] = content
                                log(f"Added section: {section}")
            else:
                warn(f"No registry entry found for topic: {self.topic}")
        trace_out()

    def _get_sibling_summaries(self, sibling_files: List[str]) -> Dict[str, str]:
        trace_in()
        summaries = {}
        log(f"Processing {len(sibling_files)} sibling files")
        for file_path in sibling_files:
            topic_name = Path(file_path).stem
            try:
                summary_content = self.get_sub_section(topic_name, topic_name, "summary")
                if summary_content and not summary_content.startswith("Section"):
                    summaries[topic_name] = summary_content
                    log(f"Added sibling summary: {topic_name}")
                else:
                    log(f"Skipped sibling {topic_name}: no valid summary content")
            except Exception as e:
                warn(f"Failed to get summary for sibling {topic_name}: {e}")
                continue
        log(f"Collected {len(summaries)} sibling summaries")
        trace_out()
        return summaries
    
    def _get_child_directories(self, file_path: str) -> Dict[str, str]:
        trace_in()
        parent_dir = Path(file_path).parent
        child_dirs = {}
        log(f"Scanning child directories in: {parent_dir}")
        for child_dir in parent_dir.iterdir():
            if child_dir.is_dir():
                md_file = child_dir / f"{child_dir.name}.md"
                if md_file.exists():
                    try:
                        desc_content = self.get_section_description(child_dir.name, child_dir.name)
                        if desc_content and not desc_content.startswith("Section"):
                            child_dirs[child_dir.name] = desc_content
                            log(f"Added child directory: {child_dir.name}")
                        else:
                            log(f"Skipped child {child_dir.name}: no valid description")
                    except Exception as e:
                        warn(f"Failed to get description for child {child_dir.name}: {e}")
                        continue
        log(f"Collected {len(child_dirs)} child directories")
        trace_out()
        return child_dirs

    def json_output(self) -> str:
        trace_in()
        result = {}
        result[self.topic] = {}
        main_content = self.sections.get(self.topic, '')
        has_special = any(
            name.startswith('child_') or name.startswith('file_')
            for name in self.sections.keys()
        )
        log(f"Generating JSON output: {len(self.sections)} sections, special={has_special}")
        children = {}
        files = {}
        for section_name, content in self.sections.items():
            if section_name.startswith('child_'):
                child_name = section_name[6:]
                children[child_name] = content
                log(f"Added child to output: {child_name}")
            elif section_name.startswith('file_'):
                file_name = section_name[5:]
                files[file_name] = content
                log(f"Added file to output: {file_name}")
            elif section_name == self.topic:
                pass
            else:
                result[self.topic][section_name] = content
                log(f"Added section to output: {section_name}")
        if not has_special and main_content:
            result[self.topic][self.topic] = main_content
            log("Added main content to regular output")
        if has_special and (main_content or children or files):
            result[self.topic]['main'] = main_content
            if children:
                result[self.topic]['children'] = children
                log(f"Added {len(children)} children to special output")
            if files:
                result[self.topic]['files'] = files
                log(f"Added {len(files)} files to special output")
        log(f"Generated JSON output with {len(result[self.topic])} top-level keys")
        trace_out()
        return json.dumps(result)

    def get_sub_section(self, topic: str, section: str, subsection: str) -> str:
        trace_in()
        log(f"Getting subsection: {topic}.{section}.{subsection}")
        self._ensure_loaded()
        entry = self.registry.lookup(topic)
        if not entry:
            log(f"Topic {topic} not found, attempting registry rebuild")
            try:
                self.registry.rebuild()
            except ValueError as e:
                if "Duplicate help filename" in str(e):
                    warn(f"Duplicate help filename error: {e}")
                    trace_out()
                    return f"Error: {e}"
                else:
                    warn(f"Registry rebuild failed: {e}")
                    raise e
            except Exception as e:
                warn(f"Registry rebuild failed with exception: {e}")
                raise e
            entry = self.registry.lookup(topic)
        if not entry:
            available = ', '.join(sorted(self.registry.all_topics()))
            warn(f"Help file '{topic}' not found after rebuild")
            trace_out()
            return f"Help file '{topic}' not found. Available files: {available}"
        section_key = f"{section}.{subsection}"
        sections = entry['sections']
        slice_info = sections.get(section_key)
        if not slice_info:
            available_sections = ', '.join(sections.keys())
            warn(f"Section '{section_key}' not found in topic '{topic}'")
            trace_out()
            return f"Section '{section_key}' not found. Available sections: {available_sections}"
        content = get_content_from_file(entry['file'], slice_info)
        log(f"Retrieved content: {len(content)} characters")
        trace_out()
        return content

    def get_section(self, topic: str, section: str) -> str:
        trace_in()
        log(f"Getting full text section: {topic}.{section}")
        result = self.get_sub_section(topic, section, "full_text")
        trace_out()
        return result
    
    def get_section_summary(self, topic: str, section: str) -> str:
        trace_in()
        log(f"Getting summary section: {topic}.{section}")
        result = self.get_sub_section(topic, section, "summary")
        trace_out()
        return result
    
    def get_section_description(self, topic: str, section: str) -> str:
        trace_in()
        log(f"Getting description section: {topic}.{section}")
        result = self.get_sub_section(topic, section, "description")
        trace_out()
        return result

    def get_help(self, topic: str) -> str:
        trace_in()
        log(f"Getting all help for topic: {topic}")
        self._ensure_loaded()
        entry = self.registry.lookup(topic)
        if not entry:
            available = ', '.join(sorted(self.registry.all_topics()))
            warn(f"Help file '{topic}' not found")
            trace_out()
            return json.dumps({"error": f"Help file '{topic}' not found. Available files: {available}"})
        sections = entry['sections']
        combined_json = {}
        main_sections = {}
        log(f"Processing {len(sections)} sections")
        for section_key, range_info in sections.items():
            section, sub_section = section_key.split('.', 1)
            if section not in main_sections:
                main_sections[section] = {}
            content = get_content_from_file(entry['file'], range_info)
            main_sections[section][sub_section] = content
            log(f"Added section: {section_key}")
        for section_name, subsections in main_sections.items():
            for sub_name, content in subsections.items():
                combined_json[sub_name] = content
        log(f"Generated combined JSON with {len(combined_json)} entries")
        trace_out()
        return json.dumps(combined_json)

    def clear_cache(self):
        trace_in()
        log("Clearing help query cache")
        self.registry.clear()
        trace_out()

    def _ensure_loaded(self) -> None:
        trace_in()
        if not self.registry._loaded:
            log("Registry not loaded, attempting to load")
            if not self.registry.load():
                log("Registry load failed, attempting rebuild")
                try:
                    self.registry.rebuild()
                    log("Registry rebuild successful")
                except ValueError as e:
                    if "Duplicate help filename" in str(e):
                        warn(f"Duplicate help filename error: {e}")
                        trace_out()
                        return
                    else:
                        warn(f"Registry rebuild failed: {e}")
                        raise e
                except Exception as e:
                    warn(f"Registry rebuild failed with exception: {e}")
                    raise e
            else:
                log("Registry load successful")
        else:
            log("Registry already loaded")
        trace_out()

@register_cache_cleanup('help_registry', cache_dir='hh/help/cache')
def cleanup_help_registry_cache():
    """Clean up help registry cache"""
    trace_in()
    
    # Get the cache directory path (repo and deployment)
    removed_files = []
    candidate_files = [Path(__file__).parent / "cache" / "help_registry.tsv"]
    for root in get_deployment_paths():
        candidate_files.append(root / 'hh' / 'help' / 'cache' / 'help_registry.tsv')
    
    # Remove help_registry.tsv
    for registry_file in candidate_files:
        if registry_file.exists():
            registry_file.unlink()
            removed_files.append(str(registry_file))
            log(f"Removed help registry cache: {registry_file}")
        else:
            debug(f"Help registry cache file does not exist: {registry_file}")
    
    trace_out()
    
    return {
        'success': True,
        'cache_files': len(removed_files),
        'cache_files_list': removed_files
    }
