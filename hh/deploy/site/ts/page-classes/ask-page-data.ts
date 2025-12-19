/**
 * AskPageData - Handles ask pages with status, meta, and sort_order fields.
 * Extends WorkPageData which provides shared work page functionality.
 */

import { WorkPageData } from './work-page-data.js';
import { GetPageResponse, FieldMapping } from '../page-data.js';

export class AskPageData extends WorkPageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for ask specific fields.
   * Base WorkPageData already provides status and sort_order mappings.
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings() // Include base page mappings (name, text) and work page mappings (status, sort_order)
      // Ask specific mappings can be added here in the future
    ];
  }
}
