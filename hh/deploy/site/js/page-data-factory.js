/**
 * PageData Factory - Creates appropriate PageData instance based on page class type.
 * Uses dynamically generated registry from page-classes-registry.js.
 */
import { PageData } from './page-data.js';
import { PAGE_CLASS_REGISTRY } from './page-classes-registry.js';
export class PageDataFactory {
    /**
     * Create appropriate PageData instance based on page class type.
     * Uses dynamically generated registry that includes both hh/ and ext/ page classes.
     */
    static create(data) {
        const className = data.page.class;
        // Handle aliases (multiple class names mapping to same PageData class)
        const aliasMap = {
            'mcp_action_request': 'mcp_action', // mcp_action_request is alias for mcp_action
        };
        // Resolve alias if needed
        const resolvedClassName = aliasMap[className] || className;
        // Look up class in registry
        const PageClass = PAGE_CLASS_REGISTRY[resolvedClassName];
        if (PageClass) {
            return new PageClass(data);
        }
        // Fall back to base PageData if class not found in registry
        return new PageData(data);
    }
}
