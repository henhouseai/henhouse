from typing import Dict, Any, Union
from hh.tp.tp_decorator_registry import register_tp_decorator
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.gateway import get_gateway

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


@register_tp_decorator('infographic')
def infographic_decorator(text: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    """Text processor decorator that adds infographic CSS/JS links to the HTML header and returns the HTML structure.
    
    Usage: @infographic('infographic-id')
    Example: @infographic('gateway-access-methods')
    """
    trace_in()
    try:
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available in infographic decorator")
            trace_out()
            return {
                "type": "custom",
                "value": ""
            }
        
        # Get infographic ID from first argument (arg0)
        infographic_id = kwargs.get('arg0', '')
        if not infographic_id:
            warn("No infographic ID provided to @infographic decorator. Usage: @infographic('infographic-id')")
            trace_out()
            return {
                "type": "custom",
                "value": ""
            }
        
        log(f"Infographic decorator called with ID: {infographic_id}")
        
        # Add CSS link
        gateway.response.add_css_link("/site/css/infographic-viewer.css")
        log("Added infographic CSS link via gateway")
        
        # Add core JS links only (no editor files, no layout.js)
        js_files = [
            "infographic-glossary-json.js",
            "infographic-gateway-access-methods-json.js",
            "infographic-gateway-architecture-json.js",
            "infographic-request-response-pipeline-json.js",
            "infographic-http-deployment-architecture-json.js",
            "infographic-project-folder-hierarchy-json.js",
            "infographic-json.js",
            "infographic-state.js",
            "infographic-glossary.js",
            "infographic-canvas.js",
            "infographic-data.js",
            "infographic-rendering.js",
            "infographic-interaction.js",
            "infographic-main.js"
        ]
        
        for js_file in js_files:
            gateway.response.add_js_link(f"/site/js/{js_file}")
            log(f"Added infographic JS link via gateway: {js_file}")
        
        # Return minimal HTML structure (no sidebar, just canvas + zoom controls)
        # Include inline script to set the infographic ID for filtering
        html_content = f"""    <script>
// Set the infographic ID to display (deploy mode)
window.infographicDeployId = {repr(infographic_id)};
</script>
    <div class="container">
        <div class="canvas-container">
            <div class="zoom-controls">
                <button class="zoom-button" onclick="zoomIn()" title="Zoom In">+</button>
                <button class="zoom-button" onclick="zoomOut()" title="Zoom Out">−</button>
                <button class="zoom-button" onclick="zoomToFit()" title="Zoom to Fit">⌂</button>
            </div>
            <svg id="canvas"></svg>
        </div>
    </div>

    <!-- Startup Overlay -->
    <div id="startupOverlay" class="startup-overlay"></div>

    <!-- Glossary Modal Overlay -->
    <div id="glossaryOverlay" class="glossary-overlay" onclick="dismissGlossaryModal(event)">
        <div class="glossary-modal" onclick="event.stopPropagation()">
            <button class="close-button" onclick="dismissGlossaryModal()" title="Close">×</button>
            <a id="glossaryModalPageLink" class="page-link-button" href="#" style="display: none;" title="View full page">View full page</a>
            <h3 id="glossaryModalTitle"></h3>
            <p id="glossaryModalDescription"></p>
        </div>
    </div>"""
        
        trace_out()
        return {
            "type": "custom",
            "value": html_content
        }
    except Exception as e:
        warn(f"Infographic decorator raised an exception: {e}")
        trace_out()
        return {
            "type": "custom",
            "value": ""
        }

