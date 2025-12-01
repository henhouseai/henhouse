/**
 * MCPRequestPageData - Handles MCP request pages with transaction fields.
 * Dynamic fields are automatically discovered by base class.
 */
import { PageData } from '../page-data.js';
export class MCPRequestPageData extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for MCP request specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // MCP request specific mappings - all fields can be updated together
            {
                fields: ['input_request', 'output_response', 'status', 'create_request', 'read_request',
                    'update_request', 'delete_request', 'create_executed', 'read_executed',
                    'update_executed', 'delete_executed'],
                mcpTool: 'modify_mcp_request',
                priority: 1, // Group operation - lower priority than individual setters
                buildParams: (fields, values, pageId) => {
                    const params = { page_id: pageId };
                    // Only include fields that are actually being changed
                    fields.forEach(field => {
                        if (values[field] !== undefined) {
                            params[field] = values[field];
                        }
                    });
                    return params;
                }
            }
        ];
    }
}
