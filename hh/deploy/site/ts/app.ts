/**
 * Main application entry point and action manager.
 * Handles action loading, menu building, and handler attachment.
 * All actual handlers live in PageData classes.
 */

import { getSeedData, SeedData } from './seed.js';
import { RPCClient } from './rpc-client.js';
import { PageManager } from './page-manager.js';
import { AppAction } from './page-data.js';
import { initializeViewToggle } from './view-toggle.js';

class ActionManager {
  private rpc: RPCClient;
  private seedData: SeedData;
  private hotCacheActionIds: Set<string> = new Set(); // Track hot-cache loaded action IDs

  constructor() {
    this.rpc = new RPCClient();
    this.seedData = getSeedData();
  }

  /**
   * Load page data and set up app actions from get_page response.
   */
  async loadPageAndSetupActions(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      console.warn('No page ID found in seed data, skipping page load');
      return;
    }

    try {
      // Initialize hot-cache action tracking from server-rendered elements
      this.initializeHotCacheActionsFromDOM();
      
      // Fetch page data
      const pageData = await this.rpc.getPage(pageId);
      
      // Store in PageManager
      const pageManager = PageManager.getInstance();
      pageManager.setPageData(pageData);
      
      // Get available actions separately via get_app_actions MCP tool
      const appActionsResult = await this.rpc.call('get_app_actions', {});
      const availableActions = appActionsResult.data?.available_actions || [];
      
      if (availableActions && availableActions.length > 0) {
        // Separate hot-cache actions from persistent ones
        const hotCacheActions = availableActions.filter((action: any) => action.source === 'hot_cache');
        const persistentActions = availableActions.filter((action: any) => !action.source || action.source !== 'hot_cache');
        
        // Update hot-cache actions: remove old ones not in new list, add new ones
        this.updateHotCacheActions(hotCacheActions);
        
        // Process persistent actions (only add, never remove - they're server-rendered)
        if (persistentActions.length > 0) {
          const persistentByGroup = this.groupActionsByGroup(persistentActions);
          this.addAppActionsToMenu(persistentByGroup);
          this.attachAppActionHandlers(persistentActions);
        }
      }
    } catch (error) {
      console.error('Failed to load page and setup actions:', error);
      this.rpc.showError('loadPageAndSetupActions', error);
    }
  }

  /**
   * Initialize hot-cache action tracking from server-rendered DOM elements.
   */
  private initializeHotCacheActionsFromDOM(): void {
    // Find all server-rendered hot-cache actions
    const hotCacheElements = document.querySelectorAll('a[data-source="hot_cache"]');
    Array.from(hotCacheElements).forEach((element) => {
      const actionId = element.id;
      if (actionId) {
        this.hotCacheActionIds.add(actionId);
      }
    });
  }

  /**
   * Group app actions by their group field.
   */
  private groupActionsByGroup(actions: AppAction[]): Map<string, AppAction[]> {
    const grouped = new Map<string, AppAction[]>();
    
    for (const action of actions) {
      const groupName = action.group || 'default';
      if (!grouped.has(groupName)) {
        grouped.set(groupName, []);
      }
      grouped.get(groupName)!.push(action);
    }
    
    return grouped;
  }

  /**
   * Add app actions to the menu DOM.
   */
  private addAppActionsToMenu(actionsByGroup: Map<string, AppAction[]>): void {
    const menuContainer = document.getElementById('menu');
    if (!menuContainer) {
      console.warn('Menu container not found');
      return;
    }

    for (const [groupName, actions] of actionsByGroup.entries()) {
      // Try to find existing group by data-group attribute
      let groupUl = menuContainer.querySelector(`ul.applicationActions.menuGroup[data-group="${groupName}"]`) as HTMLUListElement;
      
      if (!groupUl) {
        // Group doesn't exist, create it
        groupUl = document.createElement('ul');
        groupUl.className = 'applicationActions menuGroup';
        groupUl.setAttribute('data-group', groupName);
        
        // Create header with human-readable name (convert snake_case to spaces)
        const headerLi = document.createElement('li');
        headerLi.className = 'header';
        headerLi.textContent = groupName.replace(/_/g, ' ').toUpperCase();
        groupUl.appendChild(headerLi);
        
        // Append to menu container
        menuContainer.appendChild(groupUl);
      }
      
      // Add actions to group (check for duplicates first)
      for (const action of actions) {
        // Check if action already exists in this group
        const existingLink = groupUl.querySelector(`a#${action.id}`);
        if (existingLink) {
          continue; // Skip if already exists
        }
        
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.id = action.id;
        a.textContent = action.label || action.tool_name;
        li.appendChild(a);
        groupUl.appendChild(li);
      }
    }
  }

  /**
   * Update hot-cache actions: remove old ones not in new list, add new ones.
   */
  private updateHotCacheActions(newHotCacheActions: AppAction[]): void {
    const newActionIds = new Set(newHotCacheActions.map(action => action.id));
    const groupsToCheck = new Set<string>();
    
    // Remove hot-cache actions that are no longer in the new list
    for (const oldActionId of this.hotCacheActionIds) {
      if (!newActionIds.has(oldActionId)) {
        // Remove from DOM
        const element = document.getElementById(oldActionId);
        if (element) {
          const li = element.closest('li');
          if (li) {
            const groupUl = li.closest('ul.applicationActions.menuGroup');
            if (groupUl) {
              const groupName = groupUl.getAttribute('data-group');
              if (groupName) {
                groupsToCheck.add(groupName);
              }
            }
            li.remove();
          }
        }
      }
    }
    
    // Check and remove empty groups (only header, no action items)
    const menuContainer = document.getElementById('menu');
    if (menuContainer) {
      for (const groupName of groupsToCheck) {
        const groupUl = menuContainer.querySelector(`ul.applicationActions.menuGroup[data-group="${groupName}"]`) as HTMLUListElement;
        if (groupUl) {
          // Count non-header children (action items)
          const actionItems = groupUl.querySelectorAll('li:not(.header)');
          if (actionItems.length === 0) {
            // Group is empty (only header), remove it
            groupUl.remove();
          }
        }
      }
    }
    
    // Update tracked set
    this.hotCacheActionIds = new Set(newActionIds);
    
    // Add new hot-cache actions
    if (newHotCacheActions.length > 0) {
      const hotCacheByGroup = this.groupActionsByGroup(newHotCacheActions);
      this.addAppActionsToMenu(hotCacheByGroup);
      this.attachAppActionHandlers(newHotCacheActions);
    }
  }

  /**
   * Attach handlers for app actions using exact id as method name.
   */
  private attachAppActionHandlers(actions: AppAction[]): void {
    for (const action of actions) {
      const element = document.getElementById(action.id);
      if (!element) {
        console.warn(`App action element not found: ${action.id}`);
        continue;
      }

      // Check if handler already attached
      if (element.hasAttribute('data-handler-attached')) {
        continue;
      }

      // Find handler in PageData (via PageManager)
      const pageManager = PageManager.getInstance();
      const pageData = pageManager.getPageData();
      if (pageData && typeof (pageData as any)[action.id] === 'function') {
        element.addEventListener('click', async (e) => {
          e.preventDefault();
          try {
            await (pageData as any)[action.id].call(pageData, this.rpc);
          } catch (error) {
            this.rpc.showError(action.id, error);
          }
        });
        element.setAttribute('data-handler-attached', 'true');
      } else {
        console.warn(`Handler method not found for app action: ${action.id}`);
      }
    }
  }

  /**
   * Initialize all action handlers.
   */
  init(): void {
    // All CRUD handlers now live in PageData classes
    // No handlers registered here anymore
  }

  /**
   * Attach a click handler to an element by ID.
   */
  private attachHandler(id: string, handler: () => Promise<void>): void {
    const element = document.getElementById(id);
    if (!element) {
      console.warn(`Action handler element not found: ${id}`);
      return;
    }

    element.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        await handler();
      } catch (error) {
        this.rpc.showError(id, error);
      }
    });
  }

}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  const actionManager = new ActionManager();
  actionManager.init();
  
  // Initialize view toggle system
  initializeViewToggle();
  
  // Load page data and populate app actions
  await actionManager.loadPageAndSetupActions();
});

