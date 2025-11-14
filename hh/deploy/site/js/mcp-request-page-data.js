/**
 * MCPRequestPageData - Handles MCP request pages with transaction fields.
 * Dynamic fields are automatically discovered by base class.
 */
import { PageData } from './page-data.js';
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
