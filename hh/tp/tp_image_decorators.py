"""
TextProcessor image size decorators.
These decorators add size metadata to images in the JSON structure.
"""
from typing import Dict, Any, Union
from hh.tp.tp_decorator_registry import register_tp_decorator
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.image.image_size_tiers import IMAGE_SIZE_TIERS

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


def _find_and_tag_image(json_data: Dict[str, Any], size_value: Union[str, int, None]) -> Dict[str, Any]:
    """Recursively find resolved_image in JSON structure and add size metadata."""
    trace_in()
    if not isinstance(json_data, dict):
        trace_out()
        return json_data
    
    # Check if this dict contains a resolved_image
    if 'resolved_image' in json_data:
        # Add size metadata to the resolved_image
        resolved_image = json_data['resolved_image']
        if isinstance(resolved_image, dict):
            if isinstance(size_value, int):
                resolved_image['_preferred_size_pixels'] = size_value
            elif isinstance(size_value, str):
                resolved_image['_preferred_size'] = size_value
            log(f"Added size metadata to image: {size_value}")
    
    # Recursively check nested structures
    # Check resolved_page for image_link structures
    if 'resolved_page' in json_data:
        page = json_data['resolved_page']
        if isinstance(page, dict) and 'resolved_image' in page:
            resolved_image = page['resolved_image']
            if isinstance(resolved_image, dict):
                if isinstance(size_value, int):
                    resolved_image['_preferred_size_pixels'] = size_value
                elif isinstance(size_value, str):
                    resolved_image['_preferred_size'] = size_value
                log(f"Added size metadata to nested image: {size_value}")
    
    # Recursively process all values
    for key, value in json_data.items():
        if isinstance(value, dict):
            json_data[key] = _find_and_tag_image(value, size_value)
        elif isinstance(value, list):
            json_data[key] = [_find_and_tag_image(item, size_value) if isinstance(item, dict) else item for item in value]
    
    trace_out()
    return json_data


@register_tp_decorator('size')
def size_decorator(json_data: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    """Size decorator - sets preferred size in pixels from arg0."""
    trace_in()
    if not isinstance(json_data, dict):
        trace_out()
        return json_data
    
    size_value = kwargs.get('arg0')
    if size_value is None:
        trace_out()
        return json_data
    
    # Try to convert to int
    try:
        size_pixels = int(size_value)
        result = _find_and_tag_image(json_data, size_pixels)
        log(f"Applied size decorator with {size_pixels} pixels")
        trace_out()
        return result
    except (ValueError, TypeError):
        # If not numeric, treat as named size
        result = _find_and_tag_image(json_data, str(size_value))
        log(f"Applied size decorator with named size: {size_value}")
        trace_out()
        return result


# Special case for fullsize (uses largest available)
@register_tp_decorator('fullsize')
def fullsize_decorator(json_data: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    """Fullsize decorator - sets preferred size to fullsize."""
    trace_in()
    if not isinstance(json_data, dict):
        trace_out()
        return json_data
    
    result = _find_and_tag_image(json_data, 'fullsize')
    log("Applied fullsize decorator")
    trace_out()
    return result

# Dynamically generate decorators from IMAGE_SIZE_TIERS
for tier_name in IMAGE_SIZE_TIERS:
    decorator_name = tier_name
    exec(f"""
@register_tp_decorator('{decorator_name}')
def {decorator_name}_decorator(json_data: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    \"\"\"{decorator_name.title()} decorator - sets preferred size to {decorator_name}.\"\"\"
    trace_in()
    if not isinstance(json_data, dict):
        trace_out()
        return json_data
    
    result = _find_and_tag_image(json_data, '{decorator_name}')
    log("Applied {decorator_name} decorator")
    trace_out()
    return result
""")

