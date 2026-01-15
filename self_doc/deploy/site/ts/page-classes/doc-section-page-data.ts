/**
 * doc_section_page_data - Handles document section pages.
 * Metadata fields (section_level, sort_order, section_type) are automatically discovered by base class.
 * For now, simple extension with no custom handlers.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';

export class doc_section_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for doc_section specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings() // Include base page mappings (name, text)
      // Future: Add metadata field mappings here (section_level, sort_order, section_type)
      // when we implement modify_doc_section_metadata or similar handlers
    ];
  }
}