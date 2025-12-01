/**
 * PageData Factory - Creates appropriate PageData instance based on page class type.
 */

import { PageData, GetPageResponse } from './page-data.js';
import { SourceCodeFilePageData } from './page-classes/source-code-file-page-data.js';
import { MCPRequestPageData } from './page-classes/mcp-request-page-data.js';
import { MCPActionPageData } from './page-classes/mcp-action-page-data.js';
import { WorkDocketPageData } from './page-classes/work-docket-page-data.js';

export class PageDataFactory {
  /**
   * Create appropriate PageData instance based on page class type.
   */
  static create(data: GetPageResponse): PageData {
    const className = data.page.class;
    
    switch (className) {
      case 'source_code_file':
        return new SourceCodeFilePageData(data);
      case 'mcp_request':
        return new MCPRequestPageData(data);
      case 'mcp_action':
      case 'mcp_action_request':
        return new MCPActionPageData(data);
      case 'work_docket':
        return new WorkDocketPageData(data);
      default:
        return new PageData(data);
    }
  }
}

