"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                     Line 80
_add_badge_headers()           Line 300
_add_lower_content()           Line 225
_add_page_class_information()  Line 314
_delete_page_class_information() Line 347
_get_child_page_data()         Line 168
_get_child_row_field_type()    Line 198
_get_children_query()           Line 150
_get_display_name()            Line 127
_get_page_data()               Line 137
allow_class_inside()           Line 105
allow_duplicate_names()         Line 95
allow_inside_of()              Line 100
allow_null_names()             Line 90
auto_link_name()               Line 98
getChildrenOf()                Line 218
modify_file_path()             Line 357
modify_language()              Line 372

"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import os
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.system.dependency import register_dependency
from hh.page.page import Page
from hh.page.page_registry import get_page
from hh.page.page_class_registry import register_page_class

if TYPE_CHECKING:
    from pygments.lexers import get_lexer_by_name  # type: ignore[import-untyped]
    from pygments.formatters import HtmlFormatter  # type: ignore[import-untyped]
    from pygments.util import ClassNotFound  # type: ignore[import-untyped]
    from pygments import highlight  # type: ignore[import-untyped]

# Register pygments as a dependency
pygments_highlight: Optional[Any] = None
pygments_get_lexer_by_name: Optional[Any] = None
pygments_HtmlFormatter: Optional[Any] = None
pygments_ClassNotFound: Optional[type[BaseException]] = None

@register_dependency("pygments")
def _load_pygments():
    global pygments_highlight, pygments_get_lexer_by_name, pygments_HtmlFormatter, pygments_ClassNotFound
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import HtmlFormatter
        from pygments.util import ClassNotFound
        pygments_highlight = highlight
        pygments_get_lexer_by_name = get_lexer_by_name
        pygments_HtmlFormatter = HtmlFormatter
        pygments_ClassNotFound = ClassNotFound
        return True
    except ImportError:
        return False

_load_pygments()

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_source_code_file_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('source_code_file')
class SourceCodeFile(Page):
    """
    A derived Page class for source code files.
    Extends Page with file path and language information.
    """
    
    # Type annotations for metadata-extracted attributes
    file_path: str
    language: str
    
    def __init__(self, id: int):
        """Initialize SourceCodeFile by calling parent constructor."""
        # Call parent constructor (Page automatically extracts metadata fields)
        super().__init__(id)
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'file_path'):
            self.file_path = ''
        if not hasattr(self, 'language'):
            self.language = ''
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """Source code files allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Source code files allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """Source code files do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """Source code files cannot contain any child pages."""
        return False
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Source code files can only be inside pages."""
        return parent_class == 'page'

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """Return list of link names for source code file section header."""
        return ['Source Code Files']

    def _get_display_name(self) -> str:
        """
        Override to return filename from file_path when name is None.
        Extracts just the filename (last part after slashes) for display in breadcrumbs.
        """
        # If we have a name, use it
        if self.name:
            return self.name
        
        # Otherwise, extract filename from file_path
        if hasattr(self, 'file_path') and self.file_path:
            # Handle both forward and backslashes, get the last part
            file_path = self.file_path.replace('\\', '/')
            filename = file_path.split('/')[-1]
            if filename:
                self.display_name = filename
                self._flag_cache_refresh()
                return filename
        
        # If we don't have a filename, call super which will handle flagging cache refresh
        return super()._get_display_name()
    
    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        """Return query for getting source code file children, ordered by name."""
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'source_code_file' ORDER BY name",
            [parent_id]
        )
    
    def get_page_data(self) -> Dict[str, Any]:
        """Override to add file_path and language to full page data."""
        trace_in()
        # Get full page data from parent
        data = super().get_page_data()
        # Add source code file specific fields
        data['file_path'] = self.file_path
        data['language'] = self.language
        trace_out()
        return data
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return simplified data for source_code_file children: id, file_path, num_lines."""
        trace_in()
        data = {
            "id": self.id,
            "file_path": self.file_path
        }
        # Count lines in the file if it exists
        num_lines = 0
        if self.file_path:
            try:
                # Use gateway.files for file operations instead of direct file access
                gateway = get_gateway()
                if gateway and gateway.files:
                    # The file_path already includes context/ prefix, but files are in context/context/
                    # So we need to prepend an additional context/ to the path
                    full_file_path = f"context/{self.file_path}"
                    file_content = gateway.files.read_file_text(full_file_path)
                    if file_content is not None:
                        num_lines = len(file_content.splitlines())
                        debug(f"Successfully counted {num_lines} lines in {self.file_path}")
                    else:
                        debug(f"Could not read file {self.file_path} - file may not exist or be accessible")
                else:
                    debug("Gateway or gateway.files not available for line counting")
            except Exception as e:
                debug(f"Failed to count lines in {self.file_path}: {str(e)}")
        data['num_lines'] = num_lines
        trace_out()
        return data
    
    def _get_child_row_field_type(self) -> str:
        """Return field type based on language for source code file rows."""
        if self.language:
            return f'source_code_file_{self.language}'
        
        # Check if file has no extension - use unknown type
        if self.file_path:
            # Extract filename and check for extension
            file_path_normalized = self.file_path.replace('\\', '/')
            filename = file_path_normalized.split('/')[-1]
            # If filename has no dot at all, it has no extension
            if '.' not in filename:
                return 'source_code_file_unknown'
        
        return 'source_code_file'
    
    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'table') -> List[Dict[str, Any]]:
        """
        Override to default to 'table' mode for source code files.
        Calls the base implementation with the view_type (defaults to 'table' instead of 'tile').
        """
        return super().getChildrenOf(parent_id, view_type)
    
    def _add_lower_content(self) -> List[str]:
        """Add source code file content to lower content section with syntax highlighting."""
        if not self.file_path:
            debug("add_lower_content: No file_path set, returning empty list")
            return []
        
        # Use gateway.files for file operations instead of direct file access
        gateway = get_gateway()
        if not gateway or not gateway.files:
            debug("add_lower_content: Gateway or gateway.files not available")
            return []
        
        # The file_path already includes context/ prefix, but files are in context/context/
        # So we need to prepend an additional context/ to the path
        full_file_path = f"context/{self.file_path}"
        debug(f"add_lower_content: Attempting to read file: {self.file_path}")
        try:
            content = gateway.files.read_file_text(full_file_path)
            if content is None:
                debug(f"add_lower_content: Could not read file {self.file_path} - file may not exist or be accessible")
                return []
            
            debug(f"add_lower_content: Successfully read file {self.file_path}, returning content ({len(content)} characters)")
            
            # Check if backend is HTTP - only do Pygments highlighting for HTTP
            is_http_backend = gateway and gateway.backend == "http"
            
            if is_http_backend:
                # HTTP backend: Use Pygments for syntax highlighting
                # First content div: file path (show what's stored in database)
                file_info = f'<div class="contentHeader">{self.file_path}</div>'
                
                # Use Pygments for syntax highlighting
                language = self.language.strip() if self.language else ''
                lexer: Any = None
                if language and pygments_get_lexer_by_name is not None:
                    try:
                        lexer = pygments_get_lexer_by_name(language)  # type: ignore[misc]
                        debug(f"add_lower_content: Using lexer '{language}' for syntax highlighting")
                    except Exception as e:
                        if pygments_ClassNotFound is not None and isinstance(e, pygments_ClassNotFound):  # type: ignore[arg-type]
                            warn(f"add_lower_content: Unknown language '{language}', falling back to text")
                        else:
                            warn(f"add_lower_content: Error getting lexer for '{language}': {e}, falling back to text")
                        if pygments_get_lexer_by_name is not None:
                            lexer = pygments_get_lexer_by_name('text')  # type: ignore[misc]
                        else:
                            return [content]
                else:
                    debug("add_lower_content: No language specified, using text lexer")
                    if pygments_get_lexer_by_name is not None:
                        lexer = pygments_get_lexer_by_name('text')  # type: ignore[misc]
                    else:
                        return [content]
                
                # Configure formatter with line wrapping for markdown files
                if pygments_HtmlFormatter is None or pygments_highlight is None or lexer is None:
                    return [content]
                if language.lower() == 'markdown':
                    from hh.render.text.text import wrap
                    formatter = pygments_HtmlFormatter(wrapcode=True, lineanchors='line')  # type: ignore[misc]
                    # For markdown, wrap lines at 180 characters using intelligent word wrapping
                    wrapped_lines = []
                    for line in content.splitlines():
                        if len(line) > 170:  # Leave room to find word boundaries
                            wrapped_lines.extend(wrap(line, 180))
                        else:
                            wrapped_lines.append(line)
                    wrapped_content = '\n'.join(wrapped_lines)
                    highlighted_content = pygments_highlight(wrapped_content, lexer, formatter)  # type: ignore[misc]
                else:
                    formatter = pygments_HtmlFormatter()  # type: ignore[misc]
                    highlighted_content = pygments_highlight(content, lexer, formatter)  # type: ignore[misc]
                debug(f"add_lower_content: Syntax highlighting complete, returning HTML")
                
                # Second content div: highlighted source code
                source_code = f'<div class="content">{highlighted_content}</div>'
                
                return [file_info, source_code]
            else:
                # Non-HTTP backend (e.g., MCP): Return raw source code without HTML highlighting
                debug(f"add_lower_content: Non-HTTP backend ({gateway.backend if gateway else 'unknown'}), returning raw content")
                return [content]
        except Exception as e:
            warn(f"Failed to read file {self.file_path}: {str(e)}")
            debug(f"add_lower_content: Failed to read file {self.file_path}: {str(e)}, returning empty list")
            return []
    
    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add file_path and language to badge headers."""
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            badge_headers['page_summary']['file_path'] = self.file_path
            badge_headers['page_summary']['language'] = self.language
        else:
            warn(f"SourceCodeFile.add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    @classmethod
    def _add_page_class_information(cls, new_page_id: int):
        """
        Hook called after page creation to add source_code_files table entry.
        This is a classmethod (like PHP's static method) so it can be called on the class
        without needing an instance. Matches PHP pattern: static function addPageClassInformation()
        """
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return
        
        # Get file_path and language from gateway arguments (both optional)
        file_path = gateway.get_arg('file_path') or None
        language = gateway.get_arg('language') or None
        
        page = get_page(new_page_id)
        if not page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return
        file_path_str = file_path or ''
        language_str = language or ''
        page.set_metadata_value('file_path', file_path_str)
        page.set_metadata_value('language', language_str)
        
        # Also set the attributes directly on the page instance since it was already hydrated
        page.file_path = file_path_str
        page.language = language_str
        
        #page.reset_connection() xyzzy why are we resetting this connection?!?
        log(f"Initialized metadata for source code file page {new_page_id}")
        
        trace_out()
    
    def _delete_page_class_information(self):
        """
        Hook called before page deletion to remove source_code_files table entry.
        This is an instance method (like PHP) because it's called on the page being deleted.
        """
        trace_in()
        # No additional cleanup needed; metadata lives on the page row.
        trace_out()
    
    def modify_file_path(self, file_path: str) -> bool:
        """Modify the file_path of this source code file."""
        trace_in()
        log(f"Starting file path modification for page {self.id}: '{self.file_path}' -> '{file_path}'")
        if file_path == self.file_path:
            log("File path unchanged, no update needed")
            trace_out()
            return True
        metadata = self._get_metadata_dict()
        metadata['file_path'] = file_path
        if self._write_metadata_dict(metadata):
            self.file_path = file_path
            log(f"Successfully updated page {self.id} file path to '{file_path}'")
            self.flag_page_modification("file path changed")
        trace_out()
        return not is_error()
    
    def modify_language(self, language: str) -> bool:
        """Modify the language of this source code file."""
        trace_in()
        log(f"Starting language modification for page {self.id}: '{self.language}' -> '{language}'")
        if language == self.language:
            log("Language unchanged, no update needed")
            trace_out()
            return True
        metadata = self._get_metadata_dict()
        metadata['language'] = language
        if self._write_metadata_dict(metadata):
            self.language = language
            log(f"Successfully updated page {self.id} language to '{language}'")
            self.flag_page_modification("language changed")
        trace_out()
        return not is_error()

