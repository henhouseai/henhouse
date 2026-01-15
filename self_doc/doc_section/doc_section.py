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
def _initialize_doc_section_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('doc_section')
class DocSection(Page):
    """
    Individual section within a generated document.
    Can only be created inside document pages.

    Represents a section of a document that will be compiled
    into the final output format (markdown, HTML, etc.).

    Metadata fields (extracted automatically by Page.__init__):
    - section_level: Header level for this section (1-6, default 2 for ##)
    - sort_order: Ordering within the document (numeric)
    - section_type: Type of section ("heading", "content", "code", etc.)
    - (other section-specific fields as needed)
    """

    def __init__(self, id: int):
        """Initialize DocSection by calling parent constructor."""
        super().__init__(id)

    @classmethod
    def allow_null_names(cls) -> bool:
        """Sections can have null names (unnamed content sections)."""
        return True

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Sections allow duplicate names."""
        return True

    @classmethod
    def auto_link_name(cls) -> bool:
        """Sections don't create global links."""
        return False

    def allow_class_inside(self, target_class: str) -> bool:
        """Sections can contain standard page types."""
        return True

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Sections can only be created inside document pages."""
        return parent_class == 'document'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return section header links for doc_section pages."""
        return ['Sections']

    def _get_child_row_field_type(self) -> str:
        """Return field type for doc_section in table displays."""
        return 'doc_section'

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, List[Any]]:
        """Return query for getting DocSection children, ordered by name (sort by metadata in Python)."""
        query = """
            SELECT p.id, p.name, p.link, p.class, p.visibility, p.last_modified, p.username, p.comments
            FROM pages p
            WHERE p.parent = %s AND p.class = 'doc_section'
            ORDER BY p.name
        """
        return query, [parent_id]

    @staticmethod
    def getChildrenOf(parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """Return DocSection children of a parent page, sorted by sort_order metadata."""
        from hh.page.page_registry import get_page

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            return []

        # Get children using standard query
        query, params = DocSection._get_children_query(parent_id)
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
        Generate markdown for this section.
        Returns the formatted section content.
        """
        trace_in("Generating markdown for section")

        content_parts = []

        # Add section header if name exists
        if self.name:
            level = self.get_section_level()
            header = "#" * level
            content_parts.append(f"{header} {self.name}")

        # Add main content if it exists
        if self.text:
            content_parts.append(self.text)

        # Add child content recursively (for subsections)
        child_sections = self.get_child_sections()
        for child in child_sections:
            try:
                # Check if child has generate_markdown method (is a DocSection)
                if hasattr(child, 'generate_markdown') and callable(getattr(child, 'generate_markdown')):
                    child_markdown = child.generate_markdown()
                    if child_markdown:
                        content_parts.append(child_markdown)
            except Exception as e:
                warn(f"Failed to generate markdown for child section {child.id}: {e}")
                continue

        result = "\n\n".join(content_parts)
        trace_out(result)
        return result

    def get_section_level(self) -> int:
        """Get the header level for this section."""
        if hasattr(self, 'section_level') and self.section_level:
            try:
                level = int(self.section_level)
                if 1 <= level <= 6:
                    return level
            except (ValueError, TypeError):
                pass
        return 2  # Default to ##

    def get_child_sections(self) -> List[Page]:
        """Return child doc_section pages."""
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
                warn(f"Failed to load child section {row['id']}: {e}")
                continue

        # Sort by sort_order (extracted as attribute by Page.__init__)
        sections.sort(key=lambda s: getattr(s, 'sort_order', 999999) or 999999)

        return sections

    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """DocSection keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge

    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add doc section metadata to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['section_level'] = getattr(self, 'section_level', '')
            badge_headers['page_summary']['sort_order'] = getattr(self, 'sort_order', '')
            badge_headers['page_summary']['section_type'] = getattr(self, 'section_type', '')
        else:
            warn("DocSection._add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers

    def _get_display_name(self) -> str:
        """
        Return display name for the section.
        Uses name field if available, otherwise shows section content preview.
        """
        if self.name:
            return self.name

        # Show preview of text content
        if self.text:
            preview = self.text[:50].replace('\n', ' ').strip()
            if len(self.text) > 50:
                preview += "..."
            return preview

        return f"Section {self.id}"

    def modify_doc_section_info(self, section_level: Optional[int] = None, sort_order: Optional[int] = None, section_type: Optional[str] = None) -> bool:
        """
        Modify doc section metadata fields.
        Updates section_level, sort_order, and/or section_type.
        """
        trace_in("modify_doc_section_info")

        # Get current metadata
        metadata = self._get_metadata_dict()

        # Track changes
        changes_made = []

        # Update section_level if provided
        if section_level is not None:
            # Validate section_level
            if not isinstance(section_level, int) or not (1 <= section_level <= 6):
                warn(f"Invalid section_level {section_level}. Must be integer 1-6")
                trace_out()
                return False

            old_value = metadata.get('section_level', '')
            new_value = str(section_level)
            if new_value != old_value:
                metadata['section_level'] = new_value
                self.section_level = new_value
                changes_made.append(f"section_level: '{old_value}' -> '{new_value}'")
                log(f"Updated section_level to {section_level}")

        # Update sort_order if provided
        if sort_order is not None:
            # Validate sort_order
            if not isinstance(sort_order, int) or sort_order < 0:
                warn(f"Invalid sort_order {sort_order}. Must be non-negative integer")
                trace_out()
                return False

            old_value = metadata.get('sort_order', '')
            new_value = str(sort_order)
            if new_value != old_value:
                metadata['sort_order'] = new_value
                self.sort_order = new_value
                changes_made.append(f"sort_order: '{old_value}' -> '{new_value}'")
                log(f"Updated sort_order to {sort_order}")

        # Update section_type if provided
        if section_type is not None:
            # Validate section_type
            valid_types = ['heading', 'content', 'code', 'list', 'table']
            if section_type not in valid_types:
                warn(f"Invalid section_type '{section_type}'. Must be one of: {', '.join(valid_types)}")
                trace_out()
                return False

            old_value = metadata.get('section_type', '')
            if section_type != old_value:
                metadata['section_type'] = section_type
                self.section_type = section_type
                changes_made.append(f"section_type: '{old_value}' -> '{section_type}'")
                log(f"Updated section_type to '{section_type}'")

        # Write metadata if changes were made
        if changes_made:
            if self._write_metadata_dict(metadata):
                log(f"Successfully updated doc section {self.id}: {', '.join(changes_made)}")
                self.flag_page_modification("doc section info changed")
            else:
                warn("Failed to write metadata")
                trace_out()
                return False

        trace_out()
        return not is_error()