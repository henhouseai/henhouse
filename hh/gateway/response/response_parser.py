"""
Response class for parser (CLI) backend output.
Outputs raw text with newline joining - no additional formatting.
"""
from __future__ import annotations
from typing import List, Optional
from hh.gateway.response.response import Response

class ResponseParser(Response):
    """
    Parser backend response handler.
    Outputs raw CLI text with header rendering from metadata.
    """
    
    def get_output(self) -> str:
        """Return CLI output - includes upper_content, page_text, lower_content, then backend response."""
        parts = []
        
        # Upper content (path and badge headers)
        if self.upper_content:
            upper_content_text = "\n".join(self.upper_content)
            if upper_content_text:
                parts.append(upper_content_text)
        
        # Page text
        if self.page_text:
            parts.append(self.page_text)
        
        # Lower content (images, children, extra data)
        if self.lower_content:
            lower_content_text = "\n".join(self.lower_content)
            if lower_content_text:
                parts.append(lower_content_text)
        
        # Backend response (output buffer)
        if self.output_buffer:
            backend_response = "\n".join(self.output_buffer)
            if backend_response:
                parts.append(backend_response)
        
        return "\n".join(parts)

