"""
OCR Page renderer.
Displays OCR results for all images on a page.
Shows summary table plus individual tables for each image's OCR results.
"""

from __future__ import annotations
from typing import Dict, List, Union, Any, Mapping, cast
from hh.gateway.registry.registry import register_parser
from hh.gateway.error.error_store import report_error
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import dc, break_section, safe_str
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.response.json_standard import get_data
from hh.deploy.maint.job_queue import update_maintenance_job
from hh.gateway.error.error_store import is_error

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_render_ocr_page_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

@register_parser('ocr_page')
def ocr_page() -> bool:
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
    lines.append(render_header_block('OCR Page Results'))

    source_data = get_data(cast(Mapping[str, Any], action_response))
    log("Processing OCR page data successfully")

    # Update job status if this was a maintenance job
    job_id = source_data.get('job_id')
    error_occurred = is_error()
    ocr_status_response = source_data.get('ocr_status', 'unknown')

    if job_id:
        if error_occurred:
            update_maintenance_job(
                job_id=job_id,
                status="error",
            )
            log(f"Set job {job_id} status to error")
        elif ocr_status_response in ('success', 'no_job'):
            update_maintenance_job(
                job_id=job_id,
                status="done",
            )
            log(f"Set job {job_id} status to done")
        else:
            # Still processing or other status
            log(f"Job {job_id} still processing (status: {ocr_status_response})")

    # Extract data
    page_id = source_data.get('page_id')
    has_images = source_data.get('has_images', False)
    images_processed = source_data.get('images_processed', 0)
    ocr_status = source_data.get('ocr_status', 'unknown')
    ocr_summary = source_data.get('ocr_summary', {})

    # Create summary table
    summary_table = TableData()

    # Page information
    if page_id is not None:
        summary_table.add_row(
            'ocr_page_id',
            label='Page ID',
            value=str(page_id)
        )

    # Status
    status_display = '✅ Success' if ocr_status == 'success' else '❌ Error' if ocr_status == 'error' else '❓ Unknown'
    summary_table.add_row(
        'ocr_status',
        label='Status',
        value=status_display
    )

    # Image count
    summary_table.add_row(
        'ocr_images_available',
        label='Images Available',
        value='Yes' if has_images else 'No'
    )

    summary_table.add_row(
        'ocr_images_processed',
        label='Images Processed',
        value=str(images_processed)
    )

    # Total text extracted
    total_text_length = sum(
        summary.get('text_length', 0)
        for summary in ocr_summary.values()
    )
    summary_table.add_row(
        'ocr_total_text',
        label='Total Text Length',
        value=f"{total_text_length} characters"
    )

    lines.append(render_block(
        summary_table,
        FieldConfig()
            .add_simple(['ocr_page_id', 'ocr_status', 'ocr_images_available', 'ocr_images_processed', 'ocr_total_text']),
        table_overrides={'margin_l': 4},
        block_type='ocr_summary'
    ))

    # Add section break if we have results to show
    if ocr_summary:
        break_section(lines)

    # Create individual tables for each image's OCR results
    for image_id, image_summary in ocr_summary.items():
        # Image header
        lines.append(render_header_block(f'OCR Results - Image {image_id}'))

        image_table = TableData()

        # Image metadata
        image_table.add_row(
            'ocr_image_id',
            label='Image ID',
            value=str(image_id)
        )

        timestamp = image_summary.get('timestamp', '')
        if timestamp:
            # Format timestamp nicely
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except:
                formatted_time = timestamp
            image_table.add_row(
                'ocr_timestamp',
                label='Processed',
                value=formatted_time
            )

        confidence_count = image_summary.get('confidence_count', 0)
        image_table.add_row(
            'ocr_confidence_count',
            label='Text Regions',
            value=str(confidence_count)
        )

        text_length = image_summary.get('text_length', 0)
        image_table.add_row(
            'ocr_text_length',
            label='Text Length',
            value=f"{text_length} characters"
        )

        lines.append(render_block(
            image_table,
            FieldConfig()
                .add_simple(['ocr_image_id', 'ocr_timestamp', 'ocr_confidence_count', 'ocr_text_length']),
            table_overrides={'margin_l': 4},
            block_type='ocr_image_meta'
        ))

        # Get the actual OCR text for this image
        # Note: This renderer assumes the action response includes the full OCR text
        # In a real implementation, you might need to load the page and get the text
        ocr_text = source_data.get('ocr_text', {}).get(image_id, '')

        if ocr_text.strip():
            # Create text table
            text_table = TableData()

            text_table.add_row(
                'ocr_text_header',
                label='Extracted Text',
                value=''
            )

            # Split text into lines and add each as a separate row
            text_lines = ocr_text.split('\n')
            for i, line in enumerate(text_lines):
                if line.strip():  # Only add non-empty lines
                    text_table.add_row(
                        f'ocr_text_line_{i}',
                        label='' if i > 0 else 'Text',  # Only show "Text" label on first line
                        value=safe_str(line)
                    )

            lines.append(render_block(
                text_table,
                FieldConfig()
                    .add_simple(['ocr_text_header'] + [f'ocr_text_line_{i}' for i in range(len(text_lines) if text_lines else 1)]),
                table_overrides={'margin_l': 4},
                block_type='ocr_text'
            ))
        else:
            # No text table
            no_text_table = TableData()
            no_text_table.add_row(
                'ocr_no_text',
                label='Text',
                value='No text detected in image'
            )
            lines.append(render_block(
                no_text_table,
                FieldConfig().add_simple(['ocr_no_text']),
                table_overrides={'margin_l': 4},
                block_type='ocr_text'
            ))

        # Add section break between images (except for the last one)
        if image_id != list(ocr_summary.keys())[-1]:
            break_section(lines)

    result = finalize_output(lines)
    gateway.response.add_output(result)
    log(f"OCR page parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
