/**
 * PageData Derived Classes - Extended classes for specific page types.
 */
import { PageData } from './page-data.js';
/**
 * SourceCodeFilePageData - Handles source code file pages with path and language fields.
 * Dynamic fields (file_path, language) are automatically discovered by base class.
 */
export class SourceCodeFilePageData extends PageData {
    constructor(data) {
        super(data);
    }
    // Override MCP tool mapping if needed for specific field names
    getMCPToolName(fieldName) {
        if (fieldName === 'file_path')
            return 'modify_path';
        if (fieldName === 'language')
            return 'modify_language';
        return super.getMCPToolName(fieldName);
    }
}
/**
 * MCPRequestPageData - Handles MCP request pages with transaction fields.
 * Dynamic fields are automatically discovered by base class.
 */
export class MCPRequestPageData extends PageData {
    constructor(data) {
        super(data);
    }
    // Override MCP tool mapping if needed for specific field names
    getMCPToolName(fieldName) {
        if (fieldName === 'input_request' || fieldName === 'output_response' || fieldName === 'status') {
            return 'modify_mcp_request';
        }
        return super.getMCPToolName(fieldName);
    }
}
/**
 * MCPActionPageData - Handles MCP action request pages.
 * Dynamic fields are automatically discovered by base class.
 */
export class MCPActionPageData extends PageData {
    constructor(data) {
        super(data);
    }
    // Override MCP tool mapping if needed for specific field names
    getMCPToolName(fieldName) {
        if (fieldName === 'tool_name' || fieldName === 'arguments' || fieldName === 'extraction_spec' ||
            fieldName === 'status' || fieldName === 'result') {
            return 'modify_mcp_action_request';
        }
        return super.getMCPToolName(fieldName);
    }
}
