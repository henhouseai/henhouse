/**
 * mcp_action_page_data - Handles MCP action request pages.
 * Dynamic fields are automatically discovered by base class.
 */
import { PageData } from '../page-data.js';
export class mcp_action_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for MCP action request specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // MCP action request specific mappings - all fields can be updated together
            {
                fields: ['tool_name', 'arguments', 'extraction_spec', 'status', 'result',
                    'is_create', 'is_read', 'is_update', 'is_delete'],
                mcpTool: 'modify_mcp_action_request',
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
