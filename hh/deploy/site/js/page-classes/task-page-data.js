/**
 * task_page_data - Handles task pages with status, meta, and sort_order fields.
 * Extends work_page_data which provides shared work page functionality.
 */
import { work_page_data } from './work-page-data.js';
export class task_page_data extends work_page_data {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for task specific fields.
     * Base work_page_data already provides status and sort_order mappings.
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings() // Include base page mappings (name, text) and work page mappings (status, sort_order)
            // Task specific mappings can be added here in the future
        ];
    }
}
