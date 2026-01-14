/**
 * group_page_data - Handles group pages.
 * Metadata fields (description) are automatically discovered by base class.
 * For now, simple extension with no custom handlers.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';

export class group_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for group specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings() // Include base page mappings (name, text)
      // Future: Add metadata field mappings here (description)
      // when we implement modify_group_metadata or similar handlers
    ];
  }
}
