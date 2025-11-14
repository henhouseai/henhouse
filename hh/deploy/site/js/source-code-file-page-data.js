/**
 * SourceCodeFilePageData - Handles source code file pages with path and language fields.
 * Dynamic fields (file_path, language) are automatically discovered by base class.
 */
import { PageData } from './page-data.js';
export class SourceCodeFilePageData extends PageData {
    constructor(data) {
        super(data);
    }
    /**
     * Override to provide field mappings for source code file specific fields
     */
    getFieldMappings() {
        return [
            ...super.getFieldMappings(), // Include base page mappings (name, text)
            // Source code file specific mappings
            {
                fields: ['file_path'],
                mcpTool: 'modify_path',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    path: values['file_path']
                })
            },
            {
                fields: ['language'],
                mcpTool: 'modify_language',
                priority: 0,
                buildParams: (fields, values, pageId) => ({
                    page_id: pageId,
                    language: values['language']
                })
            }
        ];
    }
}
