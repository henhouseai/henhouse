/**
 * company_page_data - Handles company pages.
 * Extends user_page_data (inherits all UserPage behavior).
 * Additional metadata fields (company_name, tax_id, business_type) are automatically discovered by base class.
 * For now, simple extension with no custom handlers.
 */

import { user_page_data } from './user-page-data.js';
import { GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';

export class company_page_data extends user_page_data {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for company specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings() // Include user page mappings
      // Future: Add company-specific metadata field mappings here (company_name, tax_id, business_type)
      // when we implement modify_company_metadata or similar handlers
    ];
  }
}
