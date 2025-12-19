/**
 * StepPageData - Handles step pages with status, meta, and sort_order fields.
 * Extends WorkPageData which provides shared work page functionality.
 */
import { WorkPageData } from './work-page-data.js';
export class StepPageData extends WorkPageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for step specific fields.
     * Base WorkPageData already provides status and sort_order mappings.
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings() // Include base page mappings (name, text) and work page mappings (status, sort_order)
            // Step specific mappings can be added here in the future
        ];
    }
}
