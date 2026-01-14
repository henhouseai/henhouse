/**
 * user_page_data - Handles user pages.
 * Metadata fields (display_name, bio, website) are automatically discovered by base class.
 * For now, simple extension with no custom handlers.
 */
import { PageData } from '../../../../../hh/deploy/site/ts/page-data.js';
export class user_page_data extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for user specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings() // Include base page mappings (name, text)
            // Future: Add metadata field mappings here (display_name, bio, website)
            // when we implement modify_user_metadata or similar handlers
        ];
    }
}
