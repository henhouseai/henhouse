/**
 * users_container_page_data - Handles users container pages.
 * No additional fields beyond base page fields.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
export class users_container_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for users container specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings() // Include base page mappings (name, text)
            // Users container has no additional fields
        ];
    }
}
