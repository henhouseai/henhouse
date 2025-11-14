/**
 * PageManager - Singleton manager for current page data.
 * Stores PageData instance for form access and page state management.
 */

import { PageData } from './page-data.js';

export class PageManager {
  private static instance: PageManager | null = null;
  private currentPageData: PageData | null = null;

  private constructor() {
    // Private constructor for singleton pattern
  }

  /**
   * Get the singleton instance of PageManager.
   */
  static getInstance(): PageManager {
    if (!PageManager.instance) {
      PageManager.instance = new PageManager();
    }
    return PageManager.instance;
  }

  /**
   * Set the current page data.
   */
  setPageData(pageData: PageData): void {
    this.currentPageData = pageData;
  }

  /**
   * Get the current page data.
   */
  getPageData(): PageData | null {
    return this.currentPageData;
  }

  /**
   * Clear the current page data.
   */
  clearPageData(): void {
    this.currentPageData = null;
  }
}

