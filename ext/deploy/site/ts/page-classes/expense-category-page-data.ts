/**
 * expense_category_page_data - Handles expense category pages.
 * No additional fields beyond base page fields.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';

export class expense_category_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for expense category specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings() // Include base page mappings (name, text)
      // Expense category has no additional fields
    ];
  }
}

