/**
 * PageManager - Singleton manager for current page data.
 * Stores PageData instance for form access and page state management.
 */
export class PageManager {
    constructor() {
        this.currentPageData = null;
        // Private constructor for singleton pattern
    }
    /**
     * Get the singleton instance of PageManager.
     */
    static getInstance() {
        if (!PageManager.instance) {
            PageManager.instance = new PageManager();
        }
        return PageManager.instance;
    }
    /**
     * Set the current page data.
     */
    setPageData(pageData) {
        this.currentPageData = pageData;
    }
    /**
     * Get the current page data.
     */
    getPageData() {
        return this.currentPageData;
    }
    /**
     * Clear the current page data.
     */
    clearPageData() {
        this.currentPageData = null;
    }
}
PageManager.instance = null;
