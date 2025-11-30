"""
Response class for parser (CLI) backend output.
Outputs raw text with newline joining - no additional formatting.
"""
from __future__ import annotations
from typing import List, Optional
import json
from hh.gateway.response.response import Response

class ResponseParser(Response):
    """
    Parser backend response handler.
    Outputs raw CLI text with header rendering from metadata.
    """
    
    def get_output(self) -> str:
        """Return CLI output - includes upper_content, page_text, lower_content, child_pages, image_group, file_group, then backend response."""
        parts = []
        
        # Upper content (path and badge headers)
        if self.upper_content:
            upper_content_text = "\n".join(self.upper_content)
            if upper_content_text:
                parts.append(upper_content_text)
        
        # Page text
        if self.page_text:
            parts.append(self.page_text)
        
        # Lower content
        if self.lower_content:
            lower_content_text = "\n".join(self.lower_content)
            if lower_content_text:
                parts.append(lower_content_text)
        
        # Child pages
        if self.child_pages:
            child_pages_text = "\n".join(self.child_pages)
            if child_pages_text:
                parts.append(child_pages_text)
        
        # Image group
        if self.image_group:
            parts.append(self.image_group)
        
        # File group
        if self.file_group:
            parts.append(self.file_group)
        
        # Error output if present
        if self.error_output and "rendered" in self.error_output:
            parts.append(self.error_output["rendered"])
        
        # Backend response (output buffer)
        if self.output_buffer:
            backend_response = "\n".join(self.output_buffer)
            if backend_response:
                parts.append(backend_response)
        
        # Debug output if present
        if self.debug_output:
            if isinstance(self.debug_output, dict):
                if "text" in self.debug_output:
                    # HTTP/Parser debug format (text)
                    parts.append(self.debug_output["text"])
                elif "entries" in self.debug_output:
                    # MCP debug format (JSON entries) - convert to text for display
                    debug_text = json.dumps(self.debug_output, indent=2)
                    parts.append(debug_text)
            elif isinstance(self.debug_output, str):
                parts.append(self.debug_output)
        
        return "\n".join(parts)

