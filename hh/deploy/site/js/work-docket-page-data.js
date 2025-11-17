/**
 * WorkDocketPageData - Handles work docket pages with status, meta, and sort_order fields.
 * Dynamic fields (status, meta, sort_order) are automatically discovered by base class.
 */
import { PageData } from './page-data.js';
export class WorkDocketPageData extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for work docket specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // Work docket specific mappings
            {
                fields: ['status'],
                mcpTool: 'modify_status',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    status: values['status']
                })
            }
        ];
    }
}
