"""
OCR Page action script.
Performs OCR on all images attached to a page.
Delegates to the page's OCR methods if available.
"""

from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.deploy.maint.job_queue import claim_next_maintenance_job

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_ocr_page_action_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

@register_action('ocr_page')
@register_command('ocr_page')
def ocr_page() -> bool:
    trace_in()
    log("Starting OCR page processing")
    gateway = get_gateway()

    # Check if --id argument is provided
    page_id_arg = gateway.get_arg('id')
    page_id: int = 0

    if page_id_arg:
        # Manual processing with --id argument
        log(f"Processing manual request with page ID: {page_id_arg}")
        try:
            page_id = int(page_id_arg)
            log(f"Successfully converted page ID to: {page_id}")
        except ValueError:
            log(f"Failed to convert page ID argument '{page_id_arg}' to integer")
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    else:
        # Maintenance job processing - claim job from queue
        log("No --id argument provided, claiming maintenance job")
        job = claim_next_maintenance_job("ocr_page")

        if not job:
            log("No OCR job available in queue")
            gateway.response.set_action_response(success_payload({
                "operation": "ocr_page",
                "job_id": None,
                "resolution_id": None,
                "done": True,
                "has_images": False,
                "images_processed": 0,
                "ocr_status": "no_job",
                "message": "No job available"
            }))
            trace_out()
            return True

        # Extract page_id from job payload
        job_id = job["id"]
        payload = job.get("payload") or {}
        page_id = payload.get("id", 0)

        if not page_id:
            log(f"Job {job_id} missing page ID in payload")
            warn(f"Job {job_id} missing page ID in payload")
            report_error("action", f"Job {job_id} missing page ID in payload")
            trace_out()
            return False

        log(f"Processing maintenance job {job_id} for page {page_id}")

    # Load page from registry
    page = None
    if not is_error():
        log(f"Loading page {page_id} from registry")
        page = get_page(page_id=page_id)
        if not page:
            log(f"Page {page_id} not found in registry")
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
        else:
            log(f"Successfully loaded page {page_id}")

    # Verify page has required OCR methods
    if not is_error() and page is not None:
        log("Verifying page has OCR capabilities")
        required_methods = ['perform_batch_ocr', 'update_ocr_metadata', 'check_has_images']
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(page, method_name) or not callable(getattr(page, method_name)):
                missing_methods.append(method_name)

        if missing_methods:
            log(f"Page {page_id} missing required OCR methods: {missing_methods}")
            warn(f"Page {page_id} does not support OCR (missing: {missing_methods})")
            report_error("action", f"Page {page_id} does not support OCR functionality")
        else:
            log("Page has all required OCR methods")

    # Check if page has images
    has_images = False
    if not is_error() and page is not None:
        log("Checking if page has images")
        has_images = page.check_has_images()
        if not has_images:
            log(f"Page {page_id} has no images to process")
            # This is not an error - just return success with no-op
        else:
            log(f"Page {page_id} has images to process")

    # Perform OCR if page has images and capabilities
    ocr_results = {}
    if not is_error() and page is not None and has_images:
        log(f"Performing batch OCR on page {page_id}")
        ocr_results = page.perform_batch_ocr()

        if is_error():
            log("Batch OCR failed")
            # Error already reported by perform_batch_ocr
        elif ocr_results:
            log(f"Batch OCR succeeded with {len(ocr_results)} results")
            # Update metadata with results
            if page.update_ocr_metadata(ocr_results):
                log("Successfully updated OCR metadata")
            else:
                log("Failed to update OCR metadata")
                # Error already reported by update_ocr_metadata
        else:
            log("Batch OCR returned no results")
            # This shouldn't happen if has_images was true, but handle gracefully

    # Return response
    if not is_error():
        response_data: Dict[str, Any] = {
            'has_images': has_images,
            'images_processed': len(ocr_results) if ocr_results else 0,
            'ocr_status': 'success' if (has_images and ocr_results) or (not has_images) else 'error'
        }

        # Include job_id and daemon control fields if this was a maintenance job
        if 'job' in locals() and job:
            response_data['job_id'] = job['id']
            response_data['resolution_id'] = page_id
            response_data['done'] = True

        if ocr_results:
            # Include full OCR results for rendering
            response_data['ocr_text'] = {
                image_id: results['text']
                for image_id, results in ocr_results.items()
            }
            response_data['ocr_timestamps'] = {
                image_id: results['timestamp']
                for image_id, results in ocr_results.items()
            }
            response_data['ocr_confidence'] = {
                image_id: results['confidence']
                for image_id, results in ocr_results.items()
            }

            # Include summary for quick reference
            response_data['ocr_summary'] = {
                image_id: {
                    'timestamp': results['timestamp'],
                    'confidence_count': len(results['confidence'].split(',')) if results['confidence'] else 0,
                    'text_length': len(results['text'])
                }
                for image_id, results in ocr_results.items()
            }

        log("Setting action response")
        gateway.response.set_action_response(success_payload(response_data))
        log(f"Successfully processed OCR for page {page_id}")

    log(f"OCR page processing completed, success: {not is_error()}")
    trace_out()
    return not is_error()


register_maintenance_tool("ocr_page")