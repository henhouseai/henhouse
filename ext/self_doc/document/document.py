from __future__ import annotations
from typing import Dict, Any, List, Optional
from hh.page.page import Page
from hh.page.page_class_registry import register_page_class
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import is_error
from hh.gateway.gateway import get_gateway

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_document_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('document')
class Document(Page):
    """
    Container page for document sections.
    Only allows DocSection children.

    Represents a generated document (like README.md) that contains
    doc_section children in hierarchical order.

    Metadata fields (extracted automatically by Page.__init__):
    - output_filename: Target filename for generated output (e.g., "README.md")
    - output_format: Output format ("markdown", "html", etc.)
    - (other document-specific fields as needed)
    """

    def __init__(self, id: int):
        """Initialize Document by calling parent constructor."""
        super().__init__(id)

    @classmethod
    def allow_null_names(cls) -> bool:
        """Documents require names."""
        return False

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Documents allow duplicate names (within different parents)."""
        return True

    @classmethod
    def auto_link_name(cls) -> bool:
        """Documents create global links."""
        return True

    def allow_class_inside(self, target_class: str) -> bool:
        """Only allow doc_section pages inside documents."""
        return target_class == 'doc_section'

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Documents can be inside any page type."""
        return True

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return section header links for document pages."""
        return ['Documents']

    def _get_child_row_field_type(self) -> str:
        """Return field type for document in table displays."""
        return 'document'

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, List[Any]]:
        """Return query for getting Document children, ordered by name (sort by metadata in Python)."""
        query = """
            SELECT p.id, p.name, p.link, p.class, p.visibility, p.last_modified, p.username, p.comments
            FROM pages p
            WHERE p.parent = %s AND p.class = 'document'
            ORDER BY p.name
        """
        return query, [parent_id]

    @staticmethod
    def getChildrenOf(parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """Return Document children of a parent page, sorted by sort_order metadata."""
        from hh.page.page_registry import get_page

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            return []

        # Get children using standard query
        query, params = Document._get_children_query(parent_id)
        results = gateway.conn.read(query, params)

        # Load pages and sort by sort_order metadata
        children_pages = []
        for row in results:
            try:
                page = get_page(page_id=row['id'])
                if page:
                    children_pages.append(page)
            except Exception:
                continue

        # Sort by sort_order (extracted as attribute by Page.__init__)
        children_pages.sort(key=lambda p: getattr(p, 'sort_order', 999999) or 999999)

        # Format for display
        children_data = []
        if view_type == 'table':
            for child_page in children_pages:
                child_data = child_page._get_child_page_data()
                child_count = child_page.get_child_count()
                child_data['num_children'] = child_count
                child_data['field_type'] = child_page._get_child_row_field_type()
                child_data['_format'] = 'table'
                children_data.append(child_data)
        else:  # view_type == 'tile'
            for child_page in children_pages:
                child_data = child_page._get_child_page_data()
                display_name = child_page._get_display_name()
                child_data['display_name'] = display_name
                images_data = child_page.get_images_data()
                if images_data and len(images_data) > 0:
                    child_data['images'] = [images_data[0]]
                else:
                    child_data['images'] = []
                child_data['_format'] = 'tile'
                children_data.append(child_data)

        return children_data

    def generate_markdown(self) -> str:
        """
        Generate markdown content by walking doc_section children in order.
        Returns the complete markdown document.
        """
        trace_in("Generating markdown for document")

        sections = self.get_sections()
        markdown_parts = []

        for section in sections:
            try:
                # Check if section has generate_markdown method (is a DocSection)
                if hasattr(section, 'generate_markdown') and callable(getattr(section, 'generate_markdown')):
                    section_markdown = section.generate_markdown()
                    if section_markdown:
                        markdown_parts.append(section_markdown)
            except Exception as e:
                warn(f"Failed to generate markdown for section {section.id}: {e}")
                continue

        result = "\n\n".join(markdown_parts)
        trace_out(result)
        return result

    def get_sections(self) -> List[Page]:
        """Return doc_section children in correct order by sort_order."""
        from hh.page.page_registry import get_page

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            return []

        # Get all doc_section children
        query = """
            SELECT p.id
            FROM pages p
            WHERE p.parent = %s AND p.class = 'doc_section'
        """
        results = gateway.conn.read(query, [self.id])

        sections = []
        for row in results:
            try:
                section = get_page(page_id=row['id'])
                if section:
                    sections.append(section)
            except Exception as e:
                warn(f"Failed to load section {row['id']}: {e}")
                continue

        # Sort by sort_order (extracted as attribute by Page.__init__)
        sections.sort(key=lambda s: getattr(s, 'sort_order', 999999) or 999999)

        return sections

    def get_output_filename(self) -> str:
        """Get the target output filename from metadata."""
        if hasattr(self, 'output_filename') and self.output_filename:
            return self.output_filename
        # Default to document name with .md extension
        return f"{self.name or 'document'}.md"

    def get_output_format(self) -> str:
        """Get the output format from metadata."""
        if hasattr(self, 'output_format') and self.output_format:
            return self.output_format
        return "markdown"

    def modify_document_info(self, output_filename: Optional[str] = None, output_format: Optional[str] = None) -> bool:
        """
        Modify document metadata fields.
        Updates output_filename and/or output_format.
        """
        trace_in("modify_document_info")

        # Get current metadata
        metadata = self._get_metadata_dict()

        # Track changes
        changes_made = []

        # Update output_filename if provided
        if output_filename is not None:
            old_value = metadata.get('output_filename', '')
            if output_filename != old_value:
                metadata['output_filename'] = output_filename
                self.output_filename = output_filename
                changes_made.append(f"output_filename: '{old_value}' -> '{output_filename}'")
                log(f"Updated output_filename to '{output_filename}'")

        # Update output_format if provided
        if output_format is not None:
            # Validate output_format
            valid_formats = ['markdown', 'html', 'json']
            if output_format not in valid_formats:
                warn(f"Invalid output_format '{output_format}'. Must be one of: {', '.join(valid_formats)}")
                trace_out()
                return False

            old_value = metadata.get('output_format', '')
            if output_format != old_value:
                metadata['output_format'] = output_format
                self.output_format = output_format
                changes_made.append(f"output_format: '{old_value}' -> '{output_format}'")
                log(f"Updated output_format to '{output_format}'")

        # Write metadata if changes were made
        if changes_made:
            if self._write_metadata_dict(metadata):
                log(f"Successfully updated document {self.id}: {', '.join(changes_made)}")
                self.flag_page_modification("document info changed")
            else:
                warn("Failed to write metadata")
                trace_out()
                return False

        trace_out()
        return not is_error()

    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add document metadata to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['output_filename'] = getattr(self, 'output_filename', '')
            badge_headers['page_summary']['output_format'] = getattr(self, 'output_format', '')
        else:
            warn("Document._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers