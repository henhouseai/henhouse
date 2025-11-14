/**
 * MCPRequestPageData - Handles MCP request pages with transaction fields.
 * Dynamic fields are automatically discovered by base class.
 */

import { PageData, GetPageResponse } from './page-data.js';

export class MCPRequestPageData extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  // Override MCP tool mapping if needed for specific field names
  protected getMCPToolName(fieldName: string): string {
    if (fieldName === 'input_request' || fieldName === 'output_response' || fieldName === 'status') {
      return 'modify_mcp_request';
    }
    return super.getMCPToolName(fieldName);
  }
}

