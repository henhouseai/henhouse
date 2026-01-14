/**
 * groups_container_page_data - Handles groups container pages.
 * No additional fields beyond base page fields.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
export class groups_container_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for groups container specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings() // Include base page mappings (name, text)
            // Groups container has no additional fields
        ];
    }
}
