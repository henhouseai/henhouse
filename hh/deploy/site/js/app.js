/**
 * Main application entry point and action handlers.
 */
import { getSeedData } from './seed.js';
import { RPCClient } from './rpc-client.js';
import { OverlayManager } from './overlay-manager.js';
class ActionHandlers {
    constructor() {
        this.rpc = new RPCClient();
        this.seedData = getSeedData();
    }
    /**
     * Initialize all action handlers.
     */
    init() {
        this.attachHandler('test_one', () => this.handleGetPage());
        this.attachHandler('test_two', () => this.handleCommandList());
        this.attachHandler('test_three', () => this.handleActionList());
        this.attachHandler('test_four', () => this.handleBackendList());
        this.attachHandler('test_five', () => this.handleHttpList());
        this.attachHandler('test_six', () => this.handleParserList());
        this.attachHandler('test_seven', () => this.handleMcpList());
        // Overlay test handlers
        this.attachHandler('overlay_test_one', () => this.handleOverlayTestOne());
        this.attachHandler('overlay_test_two', () => this.handleOverlayTestTwo());
        this.attachHandler('overlay_test_three', () => this.handleOverlayTestThree());
        this.attachHandler('overlay_test_four', () => this.handleOverlayTestFour());
    }
    /**
     * Attach a click handler to an element by ID.
     */
    attachHandler(id, handler) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Action handler element not found: ${id}`);
            return;
        }
        element.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                await handler();
            }
            catch (error) {
                this.rpc.showError(id, error);
            }
        });
    }
    /**
     * Handle test_one: get_page
     */
    async handleGetPage() {
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
    async handleCommandList() {
        const result = await this.rpc.call('command_list', {});
        alert(`command_list result:\n${JSON.stringify(result, null, 2)}`);
    }
    /**
     * Handle test_three: action_list
     */
    async handleActionList() {
        const result = await this.rpc.call('action_list', {});
        alert(`action_list result:\n${JSON.stringify(result, null, 2)}`);
    }
    /**
     * Handle test_four: backend_list
     */
    async handleBackendList() {
        const result = await this.rpc.call('backend_list', {});
        alert(`backend_list result:\n${JSON.stringify(result, null, 2)}`);
    }
    /**
     * Handle test_five: http_list
     */
    async handleHttpList() {
        const result = await this.rpc.call('http_list', {});
        alert(`http_list result:\n${JSON.stringify(result, null, 2)}`);
    }
    /**
     * Handle test_six: parser_list
     */
    async handleParserList() {
        const result = await this.rpc.call('parser_list', {});
        alert(`parser_list result:\n${JSON.stringify(result, null, 2)}`);
    }
    /**
     * Handle test_seven: mcp_list
     */
    async handleMcpList() {
        const result = await this.rpc.call('mcp_list', {});
        alert(`mcp_list result:\n${JSON.stringify(result, null, 2)}`);
    }
    /**
     * Handle overlay_test_one: Simple overlay with text content
     */
    async handleOverlayTestOne() {
        const manager = OverlayManager.getInstance();
        manager.show({
            header: 'Simple Overlay Test',
            content: 'This is a simple overlay with just text content. Click Cancel or press ESC to close.',
            closable: true
        });
    }
    /**
     * Handle overlay_test_two: Overlay with HTML content
     */
    async handleOverlayTestTwo() {
        const manager = OverlayManager.getInstance();
        const htmlContent = `
      <div>
        <h3>HTML Content Test</h3>
        <p>This overlay contains <strong>HTML</strong> content with formatting.</p>
        <ul>
          <li>Item 1</li>
          <li>Item 2</li>
          <li>Item 3</li>
        </ul>
      </div>
    `;
        manager.show({
            header: 'HTML Overlay Test',
            content: htmlContent,
            closable: true
        });
    }
    /**
     * Handle overlay_test_three: Overlay with submit handler
     */
    async handleOverlayTestThree() {
        const manager = OverlayManager.getInstance();
        manager.show({
            header: 'Submit Overlay Test',
            content: 'This overlay has a submit button. Click Submit to see it in action.',
            closable: true,
            onSubmit: async () => {
                // Simulate async operation
                await new Promise(resolve => setTimeout(resolve, 500));
                alert('Submit handler executed!');
                return { success: true };
            },
            onCancel: () => {
                console.log('Overlay cancelled');
            }
        });
    }
    /**
     * Handle overlay_test_four: Multiple overlays stacked
     */
    async handleOverlayTestFour() {
        const manager = OverlayManager.getInstance();
        // Show first overlay
        manager.show({
            header: 'First Overlay',
            content: 'This is the first overlay. Click Submit to open a second overlay on top.',
            closable: true,
            onSubmit: async () => {
                // Show second overlay on top
                manager.show({
                    header: 'Second Overlay',
                    content: 'This is a second overlay stacked on top of the first. Notice the z-index stacking.',
                    closable: true,
                    onSubmit: async () => {
                        alert('Second overlay submitted!');
                        return { success: true };
                    }
                });
                return { success: true };
            }
        });
    }
}
// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const handlers = new ActionHandlers();
    handlers.init();
});
