/**
 * work_docket_page_data - Handles work docket pages with status, meta, and sort_order fields.
 * Extends work_page_data which provides shared work page functionality.
 */

import { work_page_data } from './work-page-data.js';
import { GetPageResponse, FieldMapping } from '../page-data.js';

export class work_docket_page_data extends work_page_data {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for work docket specific fields.
   * Base work_page_data already provides status mapping, so this is for future work-docket-specific fields.
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings() // Include base page mappings (name, text) and work page mappings (status)
      // Work docket specific mappings can be added here in the future
    ];
  }
}

