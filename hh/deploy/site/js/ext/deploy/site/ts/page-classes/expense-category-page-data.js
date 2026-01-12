/**
 * expense_category_page_data - Handles expense category pages.
 * No additional fields beyond base page fields.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
export class expense_category_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for expense category specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings() // Include base page mappings (name, text)
            // Expense category has no additional fields
        ];
    }
}
