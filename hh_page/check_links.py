"""Check incoming links action/command."""

from __future__ import annotations

from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import get_data, success_payload
from hh_page.page import get_page
from hh.render.render import FieldConfig, TableData, finalize_output, render_block, render_header_block

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message=None: None


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_action('check_links')
@register_command('check_links')
def check_links_action() -> bool:
    """Check for incoming links to a page and its children."""
    trace_in()
    gateway = get_gateway()

    page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
    if not page_id_arg:
        report_error('action', 'page_id or id argument required')
        trace_out()
        return False

    page_id = int(page_id_arg)
    ignore_internal = gateway.is_set('ignore_internal')

    log(f"Running check_links for page {page_id} (ignore_internal={ignore_internal})")

    page = get_page(page_id=page_id)
    if not page:
        report_error('action', f'Page {page_id} not found')
        trace_out()
        return False

    # Call page method to get incoming links data
    links_data = page.check_incoming_links(ignore_internal=ignore_internal)

    # Check if backend is API - if so, render HTML server-side
    if gateway.backend == 'api':
        from hh.render.render import FieldConfig, TableData, render_block
        from hh.render.config.config import safe_str

        # Build HTML content
        html_sections = []

        # Summary section
        num_this_page = len(links_data.get('this_page_links', []))
        num_children = links_data.get('num_children', 0)
        child_page_links = links_data.get('child_page_links', {})
        num_children_with_links = len(child_page_links)
        num_images = links_data.get('num_images', 0)
        image_links = links_data.get('image_links', {})
        num_images_with_links = len(image_links)

        summary_html = '<div class="overlay-info-text">'
        if num_this_page > 0:
            summary_html += f'<p>This page (page #{page_id}) has <strong>{num_this_page}</strong> incoming link{"s" if num_this_page != 1 else ""}.</p>'
        else:
            summary_html += f'<p>This page (page #{page_id}) has <strong>no incoming links</strong>.</p>'

        if num_children > 0:
            summary_html += f'<p>This page has <strong>{num_children}</strong> child page{"s" if num_children != 1 else ""}. <strong>{num_children_with_links}</strong> of these child page{"s" if num_children_with_links != 1 else ""} ha{"ve" if num_children_with_links != 1 else "s"} incoming links.</p>'

        if num_images > 0:
            summary_html += f'<p>This page (and all of its children pages combined) contain{"s" if num_images == 1 else ""} <strong>{num_images}</strong> image{"s" if num_images != 1 else ""}. <strong>{num_images_with_links}</strong> of these image{"s" if num_images_with_links != 1 else ""} ha{"ve" if num_images_with_links != 1 else "s"} incoming links.</p>'

        summary_html += '</div>'
        html_sections.append(('Summary', summary_html))

        # This page links table
        if num_this_page > 0:
            table = TableData()
            table.add_row(
                'this_page_links_header',
                source_id='Source ID',
                link_text='Link Text'
            )
            for link in links_data.get('this_page_links', []):
                table.add_row(
                    'incoming_link',
                    source_id=str(link['source_id']),
                    link_text=safe_str(link['link'])
                )
                table.add_page_link_to_column('source_id', link['source_id'])

            table_html = render_block(
                table,
                FieldConfig()
                    .add_header('this_page_links_header')
                    .add_simple(['incoming_link']),
                block_type='info',
                backend='http',
                table_overrides={'margin_l': 4}
            )
            html_sections.append(('This Page', table_html))

        # Child page links table
        if num_children_with_links > 0:
            table = TableData()
            table.add_row(
                'child_page_links_header',
                target_id='Target ID',
                target_name='Target Name',
                source_id='Source ID',
                link_text='Link Text'
            )

            for child_id_str, links in child_page_links.items():
                child_id = int(child_id_str)

                # Fetch child page to get name
                child_page = get_page(page_id=child_id)
                child_name = child_page.name if child_page else ''

                for link in links:
                    table.add_row(
                        'incoming_link',
                        target_id=str(child_id),
                        target_name=safe_str(child_name),
                        source_id=str(link['source_id']),
                        link_text=safe_str(link['link'])
                    )
                    table.add_page_link_to_column('target_id', child_id)
                    table.add_page_link_to_column('source_id', link['source_id'])

            table_html = render_block(
                table,
                FieldConfig()
                    .add_header('child_page_links_header')
                    .add_simple(['incoming_link']),
                block_type='info',
                backend='http',
                table_overrides={'margin_l': 4}
            )
            html_sections.append(('Child Pages', table_html))

        # Image links table
        if num_images_with_links > 0:
            table = TableData()
            table.add_row(
                'image_links_header',
                target_id='Target ID',
                source_id='Source ID'
            )

            for image_id_str, links in image_links.items():
                image_id = int(image_id_str)

                for link in links:
                    table.add_row(
                        'incoming_link',
                        target_id=str(image_id),
                        source_id=str(link['source_id'])
                    )
                    table.add_image_link_to_column('target_id', image_id)
                    table.add_page_link_to_column('source_id', link['source_id'])

            table_html = render_block(
                table,
                FieldConfig()
                    .add_header('image_links_header')
                    .add_simple(['incoming_link']),
                block_type='info',
                backend='http',
                table_overrides={'margin_l': 4}
            )
            html_sections.append(('Images', table_html))

        payload = success_payload({
            'operation': 'check_links',
            'page_id': page_id,
            'html_sections': html_sections
        })
    else:
        # Non-API backend (CLI) - return raw data
        payload = success_payload({
            'operation': 'check_links',
            'page_id': page_id,
            'links_data': links_data
        })

    gateway.response.set_action_response(payload)

    log(f"Check links completed for page {page_id}")
    trace_out()
    return not is_error()


@register_parser('check_links')
def check_links_parser() -> bool:
    """Parse and render incoming links check results for CLI."""
    trace_in()
    gateway = get_gateway()

    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False

    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data if json_data is not None else {})
        links_data = source_data.get('links_data', {})
        page_id = links_data.get('page_id')

        lines = []
        lines.append(render_header_block("l_check_links_header"))

        # Summary counts
        num_this_page = len(links_data.get('this_page_links', []))
        num_child_pages = links_data.get('num_children', 0)
        child_page_links = links_data.get('child_page_links', {})
        num_children_with_links = len(child_page_links)
        num_images = links_data.get('num_images', 0)
        image_links = links_data.get('image_links', {})
        num_images_with_links = len(image_links)

        # Summary section
        summary_lines = []
        if num_this_page > 0:
            summary_lines.append(f"This page (page #{page_id}) has {num_this_page} incoming link{'s' if num_this_page != 1 else ''}.")
        else:
            summary_lines.append(f"This page (page #{page_id}) has no incoming links.")

        if num_child_pages > 0:
            summary_lines.append(f"This page has {num_child_pages} child page{'s' if num_child_pages != 1 else ''}. {num_children_with_links} of these child page{'s' if num_children_with_links != 1 else ''} ha{'ve' if num_children_with_links != 1 else 's'} incoming links.")

        if num_images > 0:
            summary_lines.append(f"This page (and all of its children pages combined) contain{'s' if num_images == 1 else ''} {num_images} image{'s' if num_images != 1 else ''}. {num_images_with_links} of these image{'s' if num_images_with_links != 1 else ''} ha{'ve' if num_images_with_links != 1 else 's'} incoming links.")

        lines.append('\n'.join(summary_lines))

        # Detailed breakdown for this page
        if num_this_page > 0:
            table = TableData()
            table.add_row(
                "this_page_links_header",
                source_id="Source ID",
                link_text="Link Text"
            )
            for link in links_data.get('this_page_links', []):
                table.add_row(
                    "incoming_link",
                    source_id=str(link['source_id']),
                    link_text=link['link']
                )
            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_header("this_page_links_header")
                    .add_simple(["incoming_link"]),
                    block_type="info",
                    table_overrides={"margin_l": 4}
                )
            )

        # Detailed breakdown for child pages (ONE table for ALL child pages)
        if num_children_with_links > 0:
            table = TableData()
            table.add_row(
                "child_page_links_header",
                target_id="Target ID",
                target_name="Target Name",
                source_id="Source ID",
                link_text="Link Text"
            )
            for child_id, child_links in child_page_links.items():
                # Load child page to get name
                child_page = get_page(page_id=child_id)
                child_name = child_page.name if child_page else ""

                for link in child_links:
                    table.add_row(
                        "incoming_link",
                        target_id=str(child_id),
                        target_name=child_name,
                        source_id=str(link['source_id']),
                        link_text=link['link']
                    )
            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_header("child_page_links_header")
                    .add_simple(["incoming_link"]),
                    block_type="info",
                    table_overrides={"margin_l": 4}
                )
            )

        # Detailed breakdown for images (ONE table for ALL images)
        if num_images_with_links > 0:
            table = TableData()
            table.add_row(
                "image_links_header",
                target_id="Target ID",
                source_id="Source ID"
            )
            for image_id, img_links in image_links.items():
                for link in img_links:
                    table.add_row(
                        "incoming_link",
                        target_id=str(image_id),
                        source_id=str(link['source_id'])
                    )
            lines.append(
                render_block(
                    table,
                    FieldConfig()
                    .add_header("image_links_header")
                    .add_simple(["incoming_link"]),
                    block_type="info",
                    table_overrides={"margin_l": 4}
                )
            )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False
