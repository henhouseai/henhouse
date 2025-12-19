from __future__ import annotations
from typing import Dict, List, Union, Any, Mapping, cast
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data
from hh.tp.tp import TextProcessor

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


def render_usage_section(usage_data: List[Dict[str, Any]], lines: List[str]) -> None:
    trace_in()
    if not usage_data:
        log("No usage data available")
        trace_out()
        return
    log(f"Rendering usage section with {len(usage_data)} pages")
    
    usage_table = TableData()
    
    # Create header row
    usage_table.add_row(
        'image_usage_header',
        label='Pages Using This Image',
        page_id='Page ID',
        page_name='Page Name',
        usage_count='Count',
        rank_range='Rank'
    )
    
    # Create data rows for each page using this image
    for usage_item in usage_data:
        page_id_raw = usage_item.get('page_id')
        page_name = usage_item.get('page_name', 'Unknown')
        page_class = usage_item.get('page_class', 'page')
        usage_count = usage_item.get('usage_count', 0)
        ranks_str = usage_item.get('ranks', '')
        # Use the comma-separated ranks directly from the query
        rank_range = ranks_str if ranks_str else "N/A"
        
        usage_table.add_row(
            f'{page_class}_class',
            page_id=str(page_id_raw) if page_id_raw is not None else 'Unknown',
            page_name=safe_str(page_name),
            usage_count=str(usage_count),
            rank_range=rank_range
        )
        # Add page link metadata to label, page_id, and page_name columns
        if page_id_raw is not None:
            usage_table.add_page_link_to_column('label', page_id_raw)
            usage_table.add_page_link_to_column('page_id', page_id_raw)
            usage_table.add_page_link_to_column('page_name', page_id_raw)
    
    if usage_table.num_rows() > 0:
        lines.append(render_block(
            usage_table,
            FieldConfig()
                .add_header('image_usage_header')
                .add_simple(['page_class']),
            table_overrides={'margin_l': 4},
            block_type='usage'
        ))
        break_section(lines)
    trace_out()


def render_image_section(image_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    block = 'summary'
    gateway = get_gateway()
    if not gateway.is_no(block):
        log("Rendering image data section")
        
        # Calculate aspect ratio from max dimensions
        max_width = 0
        max_height = 0
        max_filesize = 0
        aspect_ratio = "N/A"
        instances = image_data.get('instances', [])
        if instances:
            max_width = max(inst.get('width', 0) for inst in instances)
            max_height = max(inst.get('height', 0) for inst in instances)
            max_filesize = max(inst.get('filesize', 0) for inst in instances)
            if max_height > 0:
                aspect_ratio = f"{max_width/max_height:.3f}"
        
        # Get folder path from first instance (trim filename)
        file_path = "N/A"
        if instances and instances[0].get('src'):
            src_path = instances[0]['src']
            # Remove filename, keep just the folder path
            last_slash = src_path.rfind('/')
            if last_slash != -1:
                file_path = src_path[:last_slash + 1]
            else:
                file_path = src_path
        
        image_summary = TableData()
        
        # Image ID
        image_id = image_data.get('id')
        if image_id:
            image_summary.add_row(
                'image_id',
                value=str(image_id)
            )
        
        # Caption
        caption = image_data.get('caption', 'untitled')
        image_summary.add_row(
            'image_caption',
            value=safe_str(caption)
        )
        
        # Aspect Ratio
        image_summary.add_row(
            'image_aspect_ratio',
            value=aspect_ratio
        )
        
        # Max Width
        image_summary.add_row(
            'image_max_width',
            value=str(max_width)
        )
        
        # Max Height
        image_summary.add_row(
            'image_max_height',
            value=str(max_height)
        )
        
        # Max Filesize
        image_summary.add_row(
            'image_max_filesize',
            value=str(max_filesize)
        )
        
        # Number of Instances
        num_instances = len(instances)
        image_summary.add_row(
            'image_num_instances',
            value=str(num_instances)
        )
        
        # File Path
        image_summary.add_row(
            'image_file_path',
            value=safe_str(file_path)
        )
        
        # Uploaded Date
        uploaded = image_data.get('uploaded')
        if uploaded:
            image_summary.add_row(
                'image_uploaded',
                value=safe_str(uploaded)
            )
        
        lines.append(render_block(
            image_summary,
            FieldConfig()
                .add_header('show_image_header')
                .add_simple(['image_id', 'image_caption', 'image_aspect_ratio', 'image_max_width', 'image_max_height', 'image_max_filesize', 'image_num_instances', 'image_file_path', 'image_uploaded']),
            table_overrides={'margin_l': 4},
            block_type=block
        ))
        break_section(lines)
    trace_out()


def render_instances_section(instances_data: List[Dict[str, Any]], lines: List[str]) -> None:
    trace_in()
    block = 'instances'
    gateway = get_gateway()
    if not gateway.is_no(block) and instances_data:
        log(f"Rendering instances section with {len(instances_data)} instances")
        
        instances_table = TableData()
        
        # Create header row
        instances_table.add_row(
            'instances_header',
            label='Image Instances',
            width='Width',
            height='Height',
            filesize='Filesize',
            filename='Filename'
        )
        
        # Create data rows for each instance
        for instance in instances_data:
            src_path = instance.get('src', '')
            instances_table.add_row(
                'instance_item',
                width=str(instance.get('width', 0)),
                height=str(instance.get('height', 0)),
                filesize=str(instance.get('filesize', 0)),
                filename=safe_str(instance.get('filename', 'N/A'))
            )
            # Add image file link metadata to filename column
            if src_path:
                instances_table.add_image_file_link_to_column('filename', src_path)
        
        if instances_table.num_rows() > 0:
            lines.append(render_block(
                instances_table,
                FieldConfig()
                    .add_header('instances_header')
                    .add_simple(['instance_item']),
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()


def render_extra_data_section(extra_data: Dict[str, Any], lines: List[str]) -> None:
    trace_in()
    block = 'extra_data'
    gateway = get_gateway()
    if not gateway.is_no(block) and extra_data:
        log(f"Rendering extra data section with {len(extra_data)} items")
        
        # Determine header label from operation field if present
        header_label = 'Action Details'  # Default
        if 'operation' in extra_data:
            operation = extra_data['operation']
            # Convert operation name to title case
            header_label = operation.replace('_', ' ').title()
        
        # Create header row
        extra_rows = TableData()
        extra_rows.add_row(
            'extra_data_header',
            label=header_label,
            value=''
        )
        
        # Programmatically create field config based on what's in extra_data
        field_config = FieldConfig()
        field_config.add_header('extra_data_header')
        
        # Create data rows for each extra field
        row_types = []
        for key, value in extra_data.items():
            # Generate row type based on key
            row_type = f'extra_data_{key}'
            
            # Handle special cases for better display
            if isinstance(value, (list, dict)):
                value = str(value)
            elif value is None:
                value = "None"
            else:
                value = str(value)
            
            # Add row with just label and value (no key column)
            extra_rows.add_row(
                row_type,
                label='',  # Label will come from .ini file
                value=safe_str(value)
            )
            row_types.append(row_type)
        
        if extra_rows.num_rows() > 0:
            # Add all row types to field config
            field_config.add_simple(row_types)
            
            lines.append(render_block(
                extra_rows,
                field_config,
                table_overrides={'margin_l': 4},
                block_type=block
            ))
            break_section(lines)
    trace_out()


@register_http('show_image')
@register_parser('show_image')
def show_image() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    action_response = gateway.response.get_action_response()
    if action_response is None:
        warn("Action response is None")
        report_error("backend", "Action response is None")
        trace_out()
        return False
    lines = []
    lines.append(render_header_block('l_show_image_header'))
    source_data = get_data(cast(Mapping[str, Any], action_response))
    log("Processing show image data successfully")
    # Render usage section first
    usage_data = source_data.get('usage', [])
    render_usage_section(usage_data, lines)
    # Render main image data section
    image_data = source_data.get('image', {})
    render_image_section(image_data, lines)
    # Render instances data section (if any)
    instances_data = source_data.get('instances', [])
    if instances_data:
        render_instances_section(instances_data, lines)
    # Render extra action-specific data section (if any)
    extra_data = {k: v for k, v in source_data.items() if k not in ['image', 'usage', 'instances', 'extra_actions']}
    if extra_data:
        render_extra_data_section(extra_data, lines)
    # Render large image at the bottom
    image_id = image_data.get('id')
    if image_id is not None:
        log(f"Rendering large image display for image {image_id}")
        # Determine final decorator based on backend and user preference
        use_json = gateway.request.get_arg('json') if gateway.request else False
        if use_json:
            final_decorator = 'mcp'
        else:
            final_decorator = gateway.backend
        # Create text with @large directive
        image_text = f'@large {{{{{{{image_id}}}}}}}'
        #image_text = '@pi(4)'
        backend_str = gateway.backend
        debug(f"Processing image text: {image_text}, backend: {backend_str}, final_decorator: {final_decorator}")
        processor = TextProcessor(final_decorator=final_decorator)
        processed_image = processor.process(image_text)
        # Output processed image directly
        processed_str = safe_str(processed_image) if processed_image is not None else ""
        lines.append(processed_str)
        break_section(lines)
    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
