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
        config.margin_l = overrides['margin_l']
    if 'margin_r' in overrides:
        config.margin_r = overrides['margin_r']
    if 'margin_t' in overrides:
        config.margin_t = overrides['margin_t']
    if 'margin_b' in overrides:
        config.margin_b = overrides['margin_b']
    if 'padl' in overrides:
        config.default_padl = overrides['padl']
    if 'padr' in overrides:
        config.default_padr = overrides['padr']
    if 'column_widths' in overrides:
        for col, width in overrides['column_widths'].items():
            config.column_widths[col] = width
    if 'column_align' in overrides:
        for col, align in overrides['column_align'].items():
            config.column_align[col] = align
    if 'column_overflow' in overrides:
        for col, overflow in overrides['column_overflow'].items():
            config.column_overflow[col] = overflow
    if 'column_valign' in overrides:
        for col, valign in overrides['column_valign'].items():
            config.column_valign[col] = valign
    if 'v_left' in overrides:
        config.v_left = overrides['v_left']
    if 'v_mid' in overrides:
        config.v_mid = overrides['v_mid']
    if 'v_right' in overrides:
        config.v_right = overrides['v_right']
    if 'h_top' in overrides:
        config.h_top = overrides['h_top']
    if 'h_header' in overrides:
        config.h_header = overrides['h_header']
    if 'h_mid' in overrides:
        config.h_mid = overrides['h_mid']
    if 'h_bot' in overrides:
        config.h_bot = overrides['h_bot']
    if 'top_left' in overrides:
        config.top_left = overrides['top_left']
    if 'top_mid' in overrides:
        config.top_mid = overrides['top_mid']
    if 'top_right' in overrides:
        config.top_right = overrides['top_right']
    if 'mid_left' in overrides:
        config.mid_left = overrides['mid_left']
    if 'mid_mid' in overrides:
        config.mid_mid = overrides['mid_mid']
    if 'mid_right' in overrides:
        config.mid_right = overrides['mid_right']
    if 'bot_left' in overrides:
        config.bot_left = overrides['bot_left']
    if 'bot_mid' in overrides:
        config.bot_mid = overrides['bot_mid']
    if 'bot_right' in overrides:
        config.bot_right = overrides['bot_right']
    if 'header_left' in overrides:
        config.header_left = overrides['header_left']
    if 'header_mid' in overrides:
        config.header_mid = overrides['header_mid']
    if 'header_right' in overrides:
        config.header_right = overrides['header_right']
    if 'has_header' in overrides:
        config.has_header = overrides['has_header']
    if 'rule_header' in overrides:
        config.rule_header = overrides['rule_header']
    if 'rule_every' in overrides:
        config.rule_every = overrides['rule_every']
    if 'separator_after_rows' in overrides:
        config.separator_after_rows = overrides['separator_after_rows']
    log(f"Applied {len(overrides)} config overrides: {list(overrides.keys())}")
    trace_out()
    return config
