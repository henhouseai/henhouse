/**
 * MCPActionPageData - Handles MCP action request pages.
 * Dynamic fields are automatically discovered by base class.
 */

import { PageData, GetPageResponse } from './page-data.js';

export class MCPActionPageData extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  // Override MCP tool mapping if needed for specific field names
  protected getMCPToolName(fieldName: string): string {
    if (fieldName === 'tool_name' || fieldName === 'arguments' || fieldName === 'extraction_spec' || 
        fieldName === 'status' || fieldName === 'result') {
      return 'modify_mcp_action_request';
    }
    return super.getMCPToolName(fieldName);
  }
}

