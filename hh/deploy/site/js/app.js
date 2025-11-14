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
        this.attachHandler('overlay_test_five', () => this.handleOverlayTestFive());
        this.attachHandler('overlay_test_six', () => this.handleOverlayTestSix());
        this.attachHandler('overlay_test_seven', () => this.handleOverlayTestSeven());
        this.attachHandler('overlay_test_eight', () => this.handleOverlayTestEight());
        // Style test handlers
        this.attachHandler('style_test_one', () => this.handleStyleTestOne());
        this.attachHandler('style_test_two', () => this.handleStyleTestTwo());
        this.attachHandler('style_test_three', () => this.handleStyleTestThree());
        this.attachHandler('style_test_four', () => this.handleStyleTestFour());
        this.attachHandler('style_test_five', () => this.handleStyleTestFive());
        this.attachHandler('style_test_six', () => this.handleStyleTestSix());
        this.attachHandler('style_test_seven', () => this.handleStyleTestSeven());
        this.attachHandler('style_test_eight', () => this.handleStyleTestEight());
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
    /**
     * Handle overlay_test_five: Focus trap test
     */
    async handleOverlayTestFive() {
        const manager = OverlayManager.getInstance();
        const htmlContent = `
      <div>
        <p>Focus Trap Test: Press Tab to cycle through focusable elements.</p>
        <p>Focus should stay trapped inside the overlay.</p>
        <input type="text" placeholder="First input" />
        <button>Button 1</button>
        <input type="text" placeholder="Second input" />
        <button>Button 2</button>
        <a href="#">Link</a>
      </div>
    `;
        manager.show({
            header: 'Focus Trap Test',
            content: htmlContent,
            closable: true
        });
    }
    /**
     * Handle overlay_test_six: Backdrop click test
     */
    async handleOverlayTestSix() {
        const manager = OverlayManager.getInstance();
        manager.show({
            header: 'Backdrop Click Test',
            content: 'Click the dark backdrop behind this overlay. It should close the overlay.',
            closable: true
        });
    }
    /**
     * Handle overlay_test_seven: Textarea Enter test
     */
    async handleOverlayTestSeven() {
        const manager = OverlayManager.getInstance();
        const htmlContent = `
      <div>
        <p>Textarea Enter Test: Press Enter in the textarea below. It should NOT trigger submit.</p>
        <p>Press Enter outside the textarea to trigger submit.</p>
        <textarea rows="4" placeholder="Type here and press Enter - should NOT submit"></textarea>
        <input type="text" placeholder="Press Enter here - SHOULD submit" />
      </div>
    `;
        manager.show({
            header: 'Textarea Enter Test',
            content: htmlContent,
            closable: true,
            onSubmit: async () => {
                alert('Submit triggered! (Enter was pressed outside textarea)');
                return { success: true };
            }
        });
    }
    /**
     * Handle overlay_test_eight: Close all test
     */
    async handleOverlayTestEight() {
        const manager = OverlayManager.getInstance();
        // Show multiple overlays
        manager.show({
            header: 'Overlay 1',
            content: 'This is overlay 1. We will open 2 more overlays, then close all at once.',
            closable: true
        });
        setTimeout(() => {
            manager.show({
                header: 'Overlay 2',
                content: 'This is overlay 2.',
                closable: true
            });
        }, 500);
        setTimeout(() => {
            manager.show({
                header: 'Overlay 3',
                content: 'This is overlay 3. Click Submit to close all overlays at once.',
                closable: true,
                onSubmit: async () => {
                    manager.closeAll();
                    alert('All overlays closed!');
                    return { success: true };
                }
            });
        }, 1000);
    }
    /**
     * Handle style_test_one: Empty content test
     */
    async handleStyleTestOne() {
        const manager = OverlayManager.getInstance();
        manager.show({
            header: 'Empty Content Test',
            content: '', // Empty string
            closable: true
        });
    }
    /**
     * Handle style_test_two: Long content test
     */
    async handleStyleTestTwo() {
        const manager = OverlayManager.getInstance();
        const longContent = Array(50).fill(0).map((_, i) => `<p>This is paragraph ${i + 1}. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>`).join('');
        manager.show({
            header: 'Long Content Test',
            content: `<div>${longContent}</div>`,
            closable: true
        });
    }
    /**
     * Handle style_test_three: Complex HTML test
     */
    async handleStyleTestThree() {
        const manager = OverlayManager.getInstance();
        const complexHTML = `
      <div>
        <h2>Complex HTML Test</h2>
        <p>This overlay contains complex nested HTML structures.</p>
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px; clear: both;">
          <h3>Nested Div</h3>
          <ul style="clear: both;">
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
          </ul>
        </div>
        <form>
          <label style="display: block; margin-bottom: 10px;">Name: <input type="text" /></label>
          <label style="display: block; margin-bottom: 10px;">Email: <input type="email" /></label>
        </form>
      </div>
    `;
        manager.show({
            header: 'Complex HTML Test',
            content: complexHTML,
            closable: true
        });
    }
    /**
     * Handle style_test_four: Error message test
     */
    async handleStyleTestFour() {
        const manager = OverlayManager.getInstance();
        manager.show({
            header: 'Error Message Test',
            content: 'Click Submit to trigger an error message. The submit button should disappear, show loading, then reappear with an error message.',
            closable: true,
            onSubmit: async () => {
                await new Promise(resolve => setTimeout(resolve, 1000));
                throw new Error('This is a test error message. The submit button should reappear after this error.');
            }
        });
    }
    /**
     * Handle style_test_five: Success message test
     */
    async handleStyleTestFive() {
        const manager = OverlayManager.getInstance();
        manager.show({
            header: 'Success Message Test',
            content: 'Click Submit to trigger a success message. The submit button should disappear, show loading, then show a success message.',
            closable: true,
            onSubmit: async () => {
                await new Promise(resolve => setTimeout(resolve, 1000));
                return { success: true };
            }
        });
    }
    /**
     * Handle style_test_six: Loading state test
     */
    async handleStyleTestSix() {
        const manager = OverlayManager.getInstance();
        manager.show({
            header: 'Loading State Test',
            content: 'Click Submit to see the loading spinner. It will take 3 seconds to complete.',
            closable: true,
            onSubmit: async () => {
                await new Promise(resolve => setTimeout(resolve, 3000));
                return { success: true };
            }
        });
    }
    /**
     * Handle style_test_seven: Special characters test
     */
    async handleStyleTestSeven() {
        const manager = OverlayManager.getInstance();
        const specialContent = `
      <div>
        <p>Special Characters Test:</p>
        <ul>
          <li>Less than: &lt;</li>
          <li>Greater than: &gt;</li>
          <li>Ampersand: &amp;</li>
          <li>Quotes: "double" and 'single'</li>
          <li>HTML tags as text: &lt;div&gt;&lt;/div&gt;</li>
        </ul>
      </div>
    `;
        manager.show({
            header: 'Special Characters Test',
            content: specialContent,
            closable: true
        });
    }
    /**
     * Handle style_test_eight: Table/Form content test
     */
    async handleStyleTestEight() {
        const manager = OverlayManager.getInstance();
        const tableFormContent = `
      <div>
        <h3>Table Content</h3>
        <table border="1" style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th>Column 1</th>
              <th>Column 2</th>
              <th>Column 3</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Row 1, Cell 1</td>
              <td>Row 1, Cell 2</td>
              <td>Row 1, Cell 3</td>
            </tr>
            <tr>
              <td>Row 2, Cell 1</td>
              <td>Row 2, Cell 2</td>
              <td>Row 2, Cell 3</td>
            </tr>
          </tbody>
        </table>
        <h3>Form Content</h3>
        <form>
          <label>Text Input: <input type="text" placeholder="Enter text" /></label><br/>
          <label>Textarea: <textarea rows="3" placeholder="Enter multiline text"></textarea></label><br/>
          <label>Select: 
            <select>
              <option>Option 1</option>
              <option>Option 2</option>
              <option>Option 3</option>
            </select>
          </label><br/>
          <label>Checkbox: <input type="checkbox" /> Check me</label><br/>
        </form>
      </div>
    `;
        manager.show({
            header: 'Table/Form Content Test',
            content: tableFormContent,
            closable: true
        });
    }
}
// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const handlers = new ActionHandlers();
    handlers.init();
});
