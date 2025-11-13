/**
 * Main application entry point and action handlers.
 */

import { getSeedData, SeedData } from './seed.js';
import { RPCClient } from './rpc-client.js';

class ActionHandlers {
  private rpc: RPCClient;
  private seedData: SeedData;

  constructor() {
    this.rpc = new RPCClient();
    this.seedData = getSeedData();
  }

  /**
   * Initialize all action handlers.
   */
  init(): void {
    this.attachHandler('test_one', () => this.handleGetPage());
    this.attachHandler('test_two', () => this.handleCommandList());
    this.attachHandler('test_three', () => this.handleActionList());
    this.attachHandler('test_four', () => this.handleBackendList());
    this.attachHandler('test_five', () => this.handleHttpList());
    this.attachHandler('test_six', () => this.handleParserList());
    this.attachHandler('test_seven', () => this.handleMcpList());
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

  /**
   * Handle test_one: get_page
   */
  private async handleGetPage(): Promise<void> {
    const pageId = this.seedData.page?.id;
    if (!pageId) {
      alert('No page ID found in seed data');
      return;
    }

    const result = await this.rpc.call('get_page', { id: String(pageId) });
    alert(`get_page result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_two: command_list
   */
  private async handleCommandList(): Promise<void> {
    const result = await this.rpc.call('command_list', {});
    alert(`command_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_three: action_list
   */
  private async handleActionList(): Promise<void> {
    const result = await this.rpc.call('action_list', {});
    alert(`action_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_four: backend_list
   */
  private async handleBackendList(): Promise<void> {
    const result = await this.rpc.call('backend_list', {});
    alert(`backend_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_five: http_list
   */
  private async handleHttpList(): Promise<void> {
    const result = await this.rpc.call('http_list', {});
    alert(`http_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_six: parser_list
   */
  private async handleParserList(): Promise<void> {
    const result = await this.rpc.call('parser_list', {});
    alert(`parser_list result:\n${JSON.stringify(result, null, 2)}`);
  }

  /**
   * Handle test_seven: mcp_list
   */
  private async handleMcpList(): Promise<void> {
    const result = await this.rpc.call('mcp_list', {});
    alert(`mcp_list result:\n${JSON.stringify(result, null, 2)}`);
  }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const handlers = new ActionHandlers();
  handlers.init();
});

