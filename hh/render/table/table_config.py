from __future__ import annotations
from typing import Union, Dict, List
from hh.render.config.config import conf_str as _cfg_conf_str, conf_int as _cfg_conf_int
from hh.render.table.table_types import TableConfig
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

def load_table_config(class_name: str) -> TableConfig:
    trace_in()
    config = TableConfig(class_name=class_name)
    config.columns_order = _cfg_conf_str(class_name, 'columns') or ''
    config.has_header = _cfg_conf_int(class_name, 'has_header') == 1
    config.rule_header = _cfg_conf_int(class_name, 'rule_header') == 1
    config.rule_every = _cfg_conf_int(class_name, 'rule_every')
    config.margin_l = _cfg_conf_int(class_name, 'margin_l')
    config.margin_r = _cfg_conf_int(class_name, 'margin_r')
    config.margin_t = _cfg_conf_int(class_name, 'margin_t')
    config.margin_b = _cfg_conf_int(class_name, 'margin_b')
    config.default_padl = _cfg_conf_int(class_name, 'padl')
    config.default_padr = _cfg_conf_int(class_name, 'padr')
    config.v_left = _cfg_conf_str(class_name, 'v_left') or ''
    config.v_mid = _cfg_conf_str(class_name, 'v_mid') or ''
    config.v_right = _cfg_conf_str(class_name, 'v_right') or ''
    config.h_top = _cfg_conf_str(class_name, 'h_top') or ''
    config.h_header = _cfg_conf_str(class_name, 'h_header') or ''
    config.h_mid = _cfg_conf_str(class_name, 'h_mid') or ''
    config.h_bot = _cfg_conf_str(class_name, 'h_bot') or ''
    config.top_left = _cfg_conf_str(class_name, 'top_left') or ''
    config.top_mid = _cfg_conf_str(class_name, 'top_mid') or ''
    config.top_right = _cfg_conf_str(class_name, 'top_right') or ''
    config.mid_left = _cfg_conf_str(class_name, 'mid_left') or ''
    config.mid_mid = _cfg_conf_str(class_name, 'mid_mid') or ''
    config.mid_right = _cfg_conf_str(class_name, 'mid_right') or ''
    config.bot_left = _cfg_conf_str(class_name, 'bot_left') or ''
    config.bot_mid = _cfg_conf_str(class_name, 'bot_mid') or ''
    config.bot_right = _cfg_conf_str(class_name, 'bot_right') or ''
    config.header_left = _cfg_conf_str(class_name, 'header_left') or ''
    config.header_mid = _cfg_conf_str(class_name, 'header_mid') or ''
    config.header_right = _cfg_conf_str(class_name, 'header_right') or ''
    log(f"Table config loaded: class={class_name}, columns={config.columns_order}, has_header={config.has_header}")
    trace_out()
    return config

def update_column_config(config: TableConfig, columns: List[str]) -> None:
    trace_in()
    assert config.column_widths is not None, "column_widths should be initialized in __post_init__"
    assert config.column_align is not None, "column_align should be initialized in __post_init__"
    assert config.column_overflow is not None, "column_overflow should be initialized in __post_init__"
    assert config.column_valign is not None, "column_valign should be initialized in __post_init__"
    for col in columns:
        if col not in config.column_widths:
            width = _cfg_conf_int(config.class_name, f'width_{col}')
            config.column_widths[col] = width if width > 0 else 0
        if col not in config.column_align:
            align = _cfg_conf_str(config.class_name, f'align_{col}')
            config.column_align[col] = align if align else 'left'
        if col not in config.column_overflow:
            overflow = _cfg_conf_str(config.class_name, f'overflow_{col}')
            config.column_overflow[col] = overflow if overflow else 'wrap'
        if col not in config.column_valign:
            valign = _cfg_conf_str(config.class_name, f'valign_{col}')
            config.column_valign[col] = valign if valign else 'top'
    log(f"Column config updated for {len(columns)} columns: {columns}")
    trace_out()

def apply_config_overrides(config: TableConfig, overrides: Dict[str, Union[str, int, bool]]) -> TableConfig:
    trace_in()
    if not overrides:
        log("No overrides provided, returning original config")
        trace_out()
        return config
    if 'margin_l' in overrides:
        val = overrides['margin_l']
        config.margin_l = val if isinstance(val, int) else int(val) if isinstance(val, (str, bool)) else 0
    if 'margin_r' in overrides:
        val = overrides['margin_r']
        config.margin_r = val if isinstance(val, int) else int(val) if isinstance(val, (str, bool)) else 0
    if 'margin_t' in overrides:
        val = overrides['margin_t']
        config.margin_t = val if isinstance(val, int) else int(val) if isinstance(val, (str, bool)) else 0
    if 'margin_b' in overrides:
        val = overrides['margin_b']
        config.margin_b = val if isinstance(val, int) else int(val) if isinstance(val, (str, bool)) else 0
    if 'padl' in overrides:
        val = overrides['padl']
        config.default_padl = val if isinstance(val, int) else int(val) if isinstance(val, (str, bool)) else 0
    if 'padr' in overrides:
        val = overrides['padr']
        config.default_padr = val if isinstance(val, int) else int(val) if isinstance(val, (str, bool)) else 0
    if 'column_widths' in overrides:
        val = overrides['column_widths']
        if isinstance(val, dict):
            for col, width in val.items():
                config.column_widths[col] = width if isinstance(width, int) else int(width) if isinstance(width, (str, bool)) else 0
    if 'column_align' in overrides:
        val = overrides['column_align']
        if isinstance(val, dict):
            for col, align in val.items():
                config.column_align[col] = str(align) if align is not None else 'left'
    if 'column_overflow' in overrides:
        val = overrides['column_overflow']
        if isinstance(val, dict):
            for col, overflow in val.items():
                config.column_overflow[col] = str(overflow) if overflow is not None else 'wrap'
    if 'column_valign' in overrides:
        val = overrides['column_valign']
        if isinstance(val, dict):
            for col, valign in val.items():
                config.column_valign[col] = str(valign) if valign is not None else 'top'
    if 'v_left' in overrides:
        val = overrides['v_left']
        config.v_left = str(val) if val is not None else ''
    if 'v_mid' in overrides:
        val = overrides['v_mid']
        config.v_mid = str(val) if val is not None else ''
    if 'v_right' in overrides:
        val = overrides['v_right']
        config.v_right = str(val) if val is not None else ''
    if 'h_top' in overrides:
        val = overrides['h_top']
        config.h_top = str(val) if val is not None else ''
    if 'h_header' in overrides:
        val = overrides['h_header']
        config.h_header = str(val) if val is not None else ''
    if 'h_mid' in overrides:
        val = overrides['h_mid']
        config.h_mid = str(val) if val is not None else ''
    if 'h_bot' in overrides:
        val = overrides['h_bot']
        config.h_bot = str(val) if val is not None else ''
    if 'top_left' in overrides:
        val = overrides['top_left']
        config.top_left = str(val) if val is not None else ''
    if 'top_mid' in overrides:
        val = overrides['top_mid']
        config.top_mid = str(val) if val is not None else ''
    if 'top_right' in overrides:
        val = overrides['top_right']
        config.top_right = str(val) if val is not None else ''
    if 'mid_left' in overrides:
        val = overrides['mid_left']
        config.mid_left = str(val) if val is not None else ''
    if 'mid_mid' in overrides:
        val = overrides['mid_mid']
        config.mid_mid = str(val) if val is not None else ''
    if 'mid_right' in overrides:
        val = overrides['mid_right']
        config.mid_right = str(val) if val is not None else ''
    if 'bot_left' in overrides:
        val = overrides['bot_left']
        config.bot_left = str(val) if val is not None else ''
    if 'bot_mid' in overrides:
        val = overrides['bot_mid']
        config.bot_mid = str(val) if val is not None else ''
    if 'bot_right' in overrides:
        val = overrides['bot_right']
        config.bot_right = str(val) if val is not None else ''
    if 'header_left' in overrides:
        val = overrides['header_left']
        config.header_left = str(val) if val is not None else ''
    if 'header_mid' in overrides:
        val = overrides['header_mid']
        config.header_mid = str(val) if val is not None else ''
    if 'header_right' in overrides:
        val = overrides['header_right']
        config.header_right = str(val) if val is not None else ''
    if 'has_header' in overrides:
        val = overrides['has_header']
        config.has_header = bool(val) if isinstance(val, (bool, int, str)) else False
    if 'rule_header' in overrides:
        val = overrides['rule_header']
        config.rule_header = bool(val) if isinstance(val, (bool, int, str)) else False
    if 'rule_every' in overrides:
        val = overrides['rule_every']
        config.rule_every = val if isinstance(val, int) else int(val) if isinstance(val, (str, bool)) else 0
    if 'separator_after_rows' in overrides:
        val = overrides['separator_after_rows']
        if isinstance(val, list):
            config.separator_after_rows = [int(x) if isinstance(x, (str, bool)) else x if isinstance(x, int) else 0 for x in val]
        else:
            config.separator_after_rows = []
    log(f"Applied {len(overrides)} config overrides: {list(overrides.keys())}")
    trace_out()
    return config
