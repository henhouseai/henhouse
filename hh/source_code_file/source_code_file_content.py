from __future__ import annotations
from typing import Dict, Any, List, Optional
import os
from hh.deploy.utils import detect_project_context
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.system.dependency import register_dependency

# Register pygments as a dependency
pygments_highlight = None
pygments_get_lexer_by_name = None
pygments_HtmlFormatter = None
pygments_ClassNotFound = None

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
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.page.page_registry import get_page

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_source_code_file_content_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class SourceCodeFileContentMixin:
    
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
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'source_code_file' ORDER BY name",
            [parent_id]
        )
    
    def _get_page_data(self) -> Dict[str, Any]:
        """Override to add file_path and language to full page data."""
        trace_in()
        # Get full page data from parent
        data = super()._get_page_data()
        # Add source code file specific fields
        data['file_path'] = self.file_path if hasattr(self, 'file_path') else ''
        data['language'] = self.language if hasattr(self, 'language') else ''
        trace_out()
        return data
    
    def _get_child_page_data(self) -> Dict[str, Any]:
        """Override to return simplified data for source_code_file children: id, file_path, num_lines."""
        trace_in()
        data = {
            "id": self.id,
            "file_path": self.file_path if hasattr(self, 'file_path') else ''
        }
        # Count lines in the file if it exists
        num_lines = 0
        if hasattr(self, 'file_path') and self.file_path:
            try:
                # Use gateway.files for file operations instead of direct file access
                gateway = get_gateway()
                if gateway and gateway.files:
                    # Try the file path as-is first (relative to current working directory)
                    file_content = gateway.files.read_file_text(self.file_path)
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
        language = self.language if hasattr(self, 'language') else ''
        if language:
            return f'source_code_file_{language}'
        
        # Check if file has no extension - use unknown type
        file_path = self.file_path if hasattr(self, 'file_path') else ''
        if file_path:
            # Extract filename and check for extension
            file_path_normalized = file_path.replace('\\', '/')
            filename = file_path_normalized.split('/')[-1]
            # If filename has no dot at all, it has no extension
            if '.' not in filename:
                return 'source_code_file_unknown'
        
        return 'source_code_file'
    
    def _add_lower_content(self) -> List[str]:
        if not self.file_path:
            debug("add_lower_content: No file_path set, returning empty list")
            return []
        
        # Use gateway.files for file operations instead of direct file access
        gateway = get_gateway()
        if not gateway or not gateway.files:
            debug("add_lower_content: Gateway or gateway.files not available")
            return []
        
        debug(f"add_lower_content: Attempting to read file: {self.file_path}")
        try:
            content = gateway.files.read_file_text(self.file_path)
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
                if language:
                    try:
                        lexer = pygments_get_lexer_by_name(language)
                        debug(f"add_lower_content: Using lexer '{language}' for syntax highlighting")
                    except pygments_ClassNotFound:
                        warn(f"add_lower_content: Unknown language '{language}', falling back to text")
                        lexer = pygments_get_lexer_by_name('text')
                else:
                    debug("add_lower_content: No language specified, using text lexer")
                    lexer = pygments_get_lexer_by_name('text')
                
                formatter = pygments_HtmlFormatter()
                highlighted_content = pygments_highlight(content, lexer, formatter)
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
        trace_in()
        badge_headers = super()._add_badge_headers()
        if 'page_summary' in badge_headers:
            # Convert None to blank string if needed
            file_path_value = '' if self.file_path is None else self.file_path
            language_value = '' if self.language is None else self.language
            badge_headers['page_summary']['file_path'] = file_path_value
            badge_headers['page_summary']['language'] = language_value
        else:
            warn(f"SourceCodeFile.add_badge_headers: 'page_summary' not found in badge_headers")
        trace_out()
        return badge_headers
    
    @classmethod
    def _add_page_class_information(cls, new_page_id: int, conn):
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
        page.set_metadata_value('file_path', file_path or '')
        page.set_metadata_value('language', language or '')
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
            self._flag_page_modification("file path changed")
        trace_out()
        return not is_error()
    
    def modify_language(self, language: str) -> bool:
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
            self._flag_page_modification("language changed")
        trace_out()
        return not is_error()

