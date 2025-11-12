from __future__ import annotations
import configparser
import os
import importlib.resources
import json
import inspect
from typing import List, Optional, Union, Any
from hh.gateway.gateway import get_gateway
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

def safe_str(value: Any, max_length: int = 1000) -> str:
    trace_in()
    if value is None:
        log("Input value is None, returning empty string")
        trace_out()
        return ""
    if isinstance(value, bool):
        result = 'true' if value else 'false'
        log(f"Converted boolean to string: {result}")
        trace_out()
        return result
    if isinstance(value, (int, float)):
        result = str(value)
        log(f"Converted numeric to string: {result}")
        trace_out()
        return result
    if isinstance(value, str):
        log(f"Input is already string, length: {len(value)}")
        trace_out()
        return value
    if isinstance(value, (dict, list)):
        try:
            json_str = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            if max_length and len(json_str) > max_length:
                result = json_str[: max_length - 3] + '...'
                log(f"JSON serialized and truncated: {len(json_str)} -> {len(result)}")
            else:
                result = json_str
                log(f"JSON serialized successfully: {len(result)} chars")
            trace_out()
            return result
        except Exception as e:
            warn(f"JSON serialization failed: {e}, falling back to str()")
            result = str(value)
            log(f"Fallback str() conversion: {len(result)} chars")
            trace_out()
            return result
    result = str(value)
    log(f"Generic str() conversion: {len(result)} chars")
    trace_out()
    return result

def _read_flat_ini(path: str) -> configparser.ConfigParser:
    trace_in()
    cfg = configparser.ConfigParser()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = '[DEFAULT]\n' + f.read()
        cfg.read_string(content)
        log(f"Configuration file loaded: {path}")
    else:
        log(f"Configuration file not found, using defaults: {path}")
    trace_out()
    return cfg

def _discover_module_config(caller_file: str, config_type: str, key: str = '') -> Optional[configparser.ConfigParser]:
    trace_in()
    stack = inspect.stack()
    hh_root = os.path.normcase(os.path.normpath(str(importlib.resources.files('hh'))))
    gateway_root = os.path.normcase(os.path.normpath(str(importlib.resources.files('hh.gateway'))))
    config_root = os.path.normcase(os.path.normpath(str(importlib.resources.files('hh.render.config'))))
    for idx, frame_info in enumerate(stack):
        frame_file = os.path.abspath(frame_info.filename)
        frame_dir = os.path.normpath(os.path.dirname(frame_file))
        frame_module = frame_info.frame.f_globals.get('__name__', '')
        if frame_module.startswith('hh.render.config'):
            continue
        if frame_module.startswith('hh.gateway') and not frame_module.startswith('hh.gateway.'):
            break
        if os.path.normcase(frame_dir) == gateway_root:
            break
        norm_dir = os.path.normpath(frame_dir)
        norm_case = os.path.normcase(norm_dir)
        if norm_case != hh_root and not norm_case.startswith(hh_root + os.sep):
            continue
        if norm_case == config_root:
            continue
        config_path = os.path.join(norm_dir, f"{config_type}.ini")
        if os.path.exists(config_path):
            log(f"Found module-specific config: {config_path}")
            cfg = _read_flat_ini(config_path)
            if key:
                k = key.lower()
                if cfg.has_option('DEFAULT', k):
                    result = cfg.get('DEFAULT', k, fallback='').strip('"')
                    if result:
                        log(f"Found key '{key}' in module config: {result}")
                        trace_out()
                        return cfg
            else:
                debug(f"No key specified for validation, returning config: {config_path}")
                trace_out()
                return cfg
    debug(f"No module-specific {config_type} config found in any hh module")
    trace_out()
    return None

_cfg_parse: Optional[configparser.ConfigParser] = None
_cfg_table: Optional[configparser.ConfigParser] = None
_section_has_output: bool = False

def _ensure_loaded() -> None:
    trace_in()
    global _cfg_parse, _cfg_table
    if _cfg_parse is None:
        parse_ini_path = importlib.resources.files('hh.render.config') / 'parse.ini'
        _cfg_parse = _read_flat_ini(str(parse_ini_path))
        log("Parse configuration loaded")
    if _cfg_table is None:
        table_ini_path = importlib.resources.files('hh.render.config') / 'table.ini'
        _cfg_table = _read_flat_ini(str(table_ini_path))
        log("Table configuration loaded")
    trace_out()

def _raw_get(key: str, caller_file: Optional[str] = None) -> str:
    trace_in()
    _ensure_loaded()
    k = key.lower()
    
    # Determine config type
    if k.startswith('t_'):
        config_type = 'table'
    elif k.startswith('l_'):
        config_type = 'label'
    elif k.startswith('max_') or k.startswith('config_'):
        config_type = 'parse'
    else:
        config_type = 'icon'
    
    # For icons and labels: check registry only (no .ini fallback)
    if config_type in ('icon', 'label'):
        try:
            from hh.render.config.config_registry import get_icon, get_label
            if config_type == 'icon':
                registry_result = get_icon(key)
                if registry_result:
                    log(f"Found icon '{key}' in registry: {registry_result}")
                    trace_out()
                    return registry_result
                # Not found - return blank emoji default
                blank_emoji = get_str('blank_emoji', caller_file) if caller_file else ''
                log(f"Icon '{key}' not found in registry, returning blank emoji default")
                trace_out()
                return blank_emoji if blank_emoji else ''
            else:  # label
                registry_result = get_label(key)
                if registry_result:
                    log(f"Found label '{key}' in registry: {registry_result}")
                    trace_out()
                    return registry_result
                # Not found - return empty string default
                log(f"Label '{key}' not found in registry, returning empty string default")
                trace_out()
                return ''
        except Exception as e:
            warn(f"Error checking registry for {config_type} '{key}': {e}")
            # Return default on error
            if config_type == 'icon':
                blank_emoji = get_str('blank_emoji', caller_file) if caller_file else ''
                trace_out()
                return blank_emoji if blank_emoji else ''
            else:
                trace_out()
                return ''
    
    # For parse and table configs: use .ini file lookup
    if config_type == 'table':
        result = _cfg_table.get('DEFAULT', k, fallback='').strip('"')  # type: ignore[union-attr]
    elif config_type == 'parse':
        result = _cfg_parse.get('DEFAULT', k, fallback='').strip('"')  # type: ignore[union-attr]
    else:
        result = ''
    
    # If not found in main config and caller_file provided, try module-specific (for parse/table only)
    if not result and caller_file:
        debug(f"Key '{key}' not found in main {config_type} config, checking module-specific config")
        module_cfg = _discover_module_config(caller_file, config_type, key)
        if module_cfg:
            result = module_cfg.get('DEFAULT', k, fallback='').strip('"')
            if result:
                log(f"Found in module config: {key}={result}")
            else:
                debug(f"Key '{key}' not found in module-specific {config_type} config either")
        else:
            debug(f"No module-specific {config_type} config available for key '{key}'")
    elif not result:
        debug(f"Key '{key}' not found in main {config_type} config and no caller_file provided")
    
    log(f"Retrieved {config_type} config: {key}={result}")
    trace_out()
    return result

def get_str(key: str, caller_file: Optional[str] = None) -> str:
    trace_in()
    result = _raw_get(key, caller_file)
    trace_out()
    return result

def get_int(key: str, caller_file: Optional[str] = None) -> int:
    trace_in()
    raw = _raw_get(key, caller_file)
    if raw == '':
        log(f"Empty string for int conversion: {key}")
        trace_out()
        return 0
    try:
        iv = int(raw)
        result = iv if iv >= 0 else 0
        log(f"Converted to int: {key}={raw} -> {result}")
        trace_out()
        return result
    except Exception as e:
        warn(f"Failed to convert to int: {key}={raw}, error: {e}")
        trace_out()
        return 0

def conf_str(cls: str, name: str, caller_file: Optional[str] = None) -> str:
    trace_in()
    result = get_str(f't_{cls}_{name}', caller_file)
    trace_out()
    return result

def conf_int(cls: str, name: str, caller_file: Optional[str] = None) -> int:
    trace_in()
    result = get_int(f't_{cls}_{name}', caller_file)
    trace_out()
    return result

def ic(name: str) -> str:
    trace_in()
    global _section_has_output
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    if gateway.is_no('icon'):
        log(f"Icon disabled via no-flags: {name}")
        trace_out()
        return ''
    
    # Get caller file for hierarchical lookup
    caller_file = inspect.currentframe().f_back.f_code.co_filename
    result = get_str(name, caller_file)
    
    if result:
        _section_has_output = True
        log(f"Icon retrieved: {name}={result}")
    else:
        # Return blank emoji if not found
        blank_emoji = get_str('blank_emoji', caller_file)
        result = blank_emoji if blank_emoji else ''
        log(f"No icon found: {name}, returning blank emoji default")
    trace_out()
    return result

def dc(name: str, add_tc: bool = False) -> str:
    trace_in()
    global _section_has_output
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return ""
    if gateway.is_no('desc'):
        log(f"Description disabled via no-flags: {name}")
        trace_out()
        return ''
    
    # Get caller file for hierarchical lookup
    caller_file = inspect.currentframe().f_back.f_code.co_filename
    result = get_str(name, caller_file)
    
    if result:
        _section_has_output = True
        if add_tc:
            result = tc() + result
            log(f"Description with tab character: {name}={result}")
        else:
            log(f"Description retrieved: {name}={result}")
    else:
        log(f"No description found: {name}")
    trace_out()
    return result

def mc(name: str) -> int:
    trace_in()
    try:
        # Get caller file for hierarchical lookup
        caller_file = inspect.currentframe().f_back.f_code.co_filename
        val = get_int(name, caller_file)
        result = val if val >= 0 else 0
        log(f"Max count retrieved: {name}={result}")
        trace_out()
        return result
    except Exception as e:
        warn(f"Failed to get max count: {name}, error: {e}")
        trace_out()
        return 0

def tc(repeat: int = 1, mode: Optional[int] = None) -> str:
    trace_in()
    # Get caller file for hierarchical lookup
    caller_file = inspect.currentframe().f_back.f_code.co_filename
    base = get_str('tab', caller_file)
    blank = get_str('blank_emoji', caller_file)
    if repeat <= 1:
        if not mode:
            log(f"Tab character: repeat={repeat}, mode=None, result={base}")
            trace_out()
            return base
        segs: List[str] = []
        if mode in (2, 4):
            segs.append(blank)
        segs.append(base)
        if mode in (3, 4):
            segs.append(blank)
        result = ''.join(segs)
        log(f"Tab character with mode: repeat={repeat}, mode={mode}, result={result}")
        trace_out()
        return result
    if not mode:
        result = base * repeat
        log(f"Tab character repeated: repeat={repeat}, mode=None, result={result}")
        trace_out()
        return result
    segs: List[str] = []
    if mode in (2, 4):
        segs.append(blank)
    for i in range(repeat):
        segs.append(base)
        if i < repeat - 1 and mode in (1, 2, 3, 4):
            segs.append(blank)
    if mode in (3, 4):
        segs.append(blank)
    result = ''.join(segs)
    log(f"Tab character complex: repeat={repeat}, mode={mode}, result={result}")
    trace_out()
    return result

def cc(name: str) -> str:
    trace_in()
    try:
        # Get caller file for hierarchical lookup
        caller_file = inspect.currentframe().f_back.f_code.co_filename
        val = get_str(name, caller_file)
        log(f"Config value retrieved: {name}={val}")
        trace_out()
        return val
    except Exception as e:
        warn(f"Failed to get config value: {name}, error: {e}")
        trace_out()
        return ''

def out(value: Union[str, int, float, bool, None]) -> str:
    trace_in()
    global _section_has_output
    s = safe_str(value)
    if s != "":
        _section_has_output = True
        log(f"Output value set: {s}")
    else:
        log("Empty output value")
    trace_out()
    return s

def break_section(lines: List[str]) -> None:
    trace_in()
    global _section_has_output
    if _section_has_output:
        lines.append("\n")
        log("Section break added to output")
    else:
        log("No section break needed")
    _section_has_output = False
    trace_out()
