/**
 * WorkDocketPageData - Handles work docket pages with status, meta, and sort_order fields.
 * Extends WorkPageData which provides shared work page functionality.
 */
import { WorkPageData } from './work-page-data.js';
export class WorkDocketPageData extends WorkPageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for work docket specific fields.
     * Base WorkPageData already provides status mapping, so this is for future work-docket-specific fields.
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings() // Include base page mappings (name, text) and work page mappings (status)
            // Work docket specific mappings can be added here in the future
        ];
    }
}
