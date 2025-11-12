import re
from pathlib import Path
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

def normalize_key(value: str) -> str:
    trace_in()
    log(f"Normalizing key: '{value}'")
    result = re.sub(r'[\s_-]+', '-', value.strip().lower())
    log(f"Normalized result: '{result}'")
    trace_out()
    return result

def map_header_to_bucket(header_text: str) -> str | None:
    trace_in()
    log(f"Mapping header to bucket: '{header_text}'")
    normalized = normalize_key(header_text)
    if normalized in ['summary', 'description', 'full-text']:
        if normalized == 'full-text':
            result = 'full_text'
            log(f"Mapped '{header_text}' -> '{result}'")
        else:
            result = normalized
            log(f"Mapped '{header_text}' -> '{result}'")
        trace_out()
        return result
    log(f"No mapping found for header: '{header_text}'")
    trace_out()
    return None

def get_default_paths() -> tuple[Path, Path]:
    trace_in()
    tools_dir = Path(__file__).resolve().parent
    help_dir = tools_dir / "help"
    registry_file = tools_dir / "cache" / "help_registry.tsv"
    log(f"Default paths - help_dir: {help_dir}, registry_file: {registry_file}")
    trace_out()
    return help_dir, registry_file
