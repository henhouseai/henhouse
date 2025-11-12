from __future__ import annotations
from typing import Dict, List, Any
from hh.gateway.registry.registry import register_parser
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data

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


def render_service_status(source_data: Dict[str, Any], lines: List[str], gateway) -> bool:
    """Render nginx service status table"""
    trace_in()
    try:
        block = 'service'
        if gateway.is_no(block):
            trace_out()
            return True
        
        nginx_service = source_data.get('nginx_service', {})
        if not nginx_service:
            debug("No nginx service data available")
            trace_out()
            return True
        
        service_data = TableData()
        service_data.add_row('service_header', value='')
        status = nginx_service.get('status', 'unknown')
        is_active = nginx_service.get('is_active', False)
        
        if is_active:
            service_data.add_row('active_service', value=safe_str(status))
            field_config = FieldConfig().add_header('service_header').add_group(['active_service'], 'status')
        else:
            service_data.add_row('inactive_service', value=safe_str(status))
            field_config = FieldConfig().add_header('service_header').add_group(['inactive_service'], 'status')
        
        rendered = render_block(
            service_data,
            field_config,
            table_overrides={'margin_l': 4},
            block_type=block
        )
        lines.append(rendered)
        break_section(lines)
        
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to render service status: {str(e)}")
        report_error("backend", f"Failed to render service status: {str(e)}")
        trace_out()
        return False


def render_summary_totals(source_data: Dict[str, Any], lines: List[str], gateway) -> bool:
    """Render summary totals table"""
    trace_in()
    try:
        block = 'summary'
        if gateway.is_no(block):
            trace_out()
            return True
        
        totals = source_data.get('totals', {})
        if not totals:
            debug("No totals data available")
            trace_out()
            return True
        

        summary_data = TableData()
        summary_data.add_row('summary_header', value='')
        summary_data.add_row('active_henhouse', value=str(totals.get('active_henhouse', 0)))
        summary_data.add_row('available_henhouse', value=str(totals.get('available_henhouse', 0)))
        summary_data.add_row('active_other', value=str(totals.get('active_other', 0)))
        summary_data.add_row('available_other', value=str(totals.get('available_other', 0)))
        
        rendered = render_block(
            summary_data,
            FieldConfig()
                .add_header('summary_header')
                .add_simple(['active_henhouse', 'available_henhouse', 'active_other', 'available_other']),
            table_overrides={'margin_l': 4},
            block_type=block
        )
        lines.append(rendered)
        break_section(lines)
        
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to render summary totals: {str(e)}")
        report_error("backend", f"Failed to render summary totals: {str(e)}")
        trace_out()
        return False


def render_site_category(category_name: str, category_label_key: str, sites: List[Dict[str, Any]], 
                         lines: List[str], gateway) -> bool:
    """Render a category of sites (DRY helper function)"""
    trace_in()
    try:
        block = category_name
        if gateway.is_no(block):
            trace_out()
            return True
        
        if not sites:
            debug(f"No sites to render for {category_name}")
            trace_out()
            return True
        
        # Sort sites: default first, then alphabetically
        sorted_sites = sorted(sites, key=lambda s: (s.get('name', '') != 'default', s.get('name', '').lower()))
        
        sites_data = TableData()
        sites_data.add_row(
            'site_header',
            name=dc('l_name')
        )
        
        for site in sorted_sites:
            ssl_enabled = site.get('ssl_enabled', False)
            if ssl_enabled:
                sites_data.add_row(
                    'site_https',
                    name=safe_str(site.get('name', 'Unknown'))
                )
            else:
                sites_data.add_row(
                    'site_http',
                    name=safe_str(site.get('name', 'Unknown'))
                )
        
        if sites_data.num_rows() > 0:
            rendered = render_block(
                sites_data,
                FieldConfig()
                    .add_header('site_header')
                    .add_simple(['site_http', 'site_https']),
                table_overrides={'margin_l': 4},
                block_type=block
            )
            lines.append(rendered)
            break_section(lines)
        
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to render {category_name}: {str(e)}")
        report_error("backend", f"Failed to render {category_name}: {str(e)}")
        trace_out()
        return False


def render_all_categories(categories: Dict[str, List[Dict[str, Any]]], lines: List[str], gateway) -> bool:
    """Render all site categories"""
    trace_in()
    try:
        category_configs = [
            ('active_henhouse', 'l_active_henhouse_header'),
            ('available_henhouse', 'l_available_henhouse_header'),
            ('active_other', 'l_active_other_header'),
            ('available_other', 'l_available_other_header')
        ]
        
        for category_name, category_label_key in category_configs:
            sites = categories.get(category_name, [])
            if not render_site_category(category_name, category_label_key, sites, lines, gateway):
                warn(f"Failed to render {category_name}")
                report_error("backend", f"Failed to render {category_name}")
                trace_out()
                return False
        
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to render categories: {str(e)}")
        report_error("backend", f"Failed to render categories: {str(e)}")
        trace_out()
        return False


@register_parser('http_status')
def http_status() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    
    json_data = gateway.response.get_action_response()
    try:
        source_data = get_data(json_data)
    except Exception as e:
        warn(f"Failed to parse action response: {str(e)}")
        report_error("backend", f"Failed to parse action response: {str(e)}")
        trace_out()
        return False
    
    lines = []
    
    # Render header
    try:
        lines.append(render_header_block('l_http_status_header'))
    except Exception as e:
        warn(f"Failed to render header: {str(e)}")
        report_error("backend", f"Failed to render header: {str(e)}")
        trace_out()
        return False
    
    # Render service status
    if not render_service_status(source_data, lines, gateway):
        trace_out()
        return False
    
    # Render summary totals
    if not render_summary_totals(source_data, lines, gateway):
        trace_out()
        return False
    
    # Render all categories
    categories = source_data.get('categories', {})
    if not render_all_categories(categories, lines, gateway):
        trace_out()
        return False
    
    try:
        result = finalize_output(lines)
        if len(result) == 0:
            warn("Backend response is empty")
        
        gateway.response.add_output(result)
        log(f"HTTP status parser completed successfully with {len(result)} characters")
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to finalize output: {str(e)}")
        report_error("backend", f"Failed to finalize output: {str(e)}")
        trace_out()
        return False
