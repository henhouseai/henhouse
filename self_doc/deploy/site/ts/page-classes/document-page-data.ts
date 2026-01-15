/**
 * document_page_data - Handles document pages.
 * Metadata fields (output_filename, output_format) are automatically discovered by base class.
 * For now, simple extension with no custom handlers.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';

export class document_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for document specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings() // Include base page mappings (name, text)
      // Future: Add metadata field mappings here (output_filename, output_format)
      // when we implement modify_document_metadata or similar handlers
    ];
  }
}