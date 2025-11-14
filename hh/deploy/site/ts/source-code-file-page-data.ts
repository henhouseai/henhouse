/**
 * SourceCodeFilePageData - Handles source code file pages with path and language fields.
 * Dynamic fields (file_path, language) are automatically discovered by base class.
 */

import { PageData, GetPageResponse } from './page-data.js';

export class SourceCodeFilePageData extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  // Override MCP tool mapping if needed for specific field names
  protected getMCPToolName(fieldName: string): string {
    if (fieldName === 'file_path') return 'modify_path';
    if (fieldName === 'language') return 'modify_language';
    return super.getMCPToolName(fieldName);
  }
}

