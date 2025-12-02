/**
 * OverlayDebugOptions - Debug options UI component for overlay forms.
 * Provides a collapsible footer section with debug/log checkboxes and filter inputs.
 */
export class OverlayDebugOptions {
    constructor() {
        this.isCollapsed = true; // Start collapsed by default
        // Create container for the entire debug section
        this.container = document.createElement('div');
        this.container.className = 'overlay-debug-section';
        // Create header with expand/collapse button
        this.headerDiv = document.createElement('div');
        this.headerDiv.className = 'contentHeader overlay';
        this.toggleBtn = document.createElement('button');
        this.toggleBtn.className = 'overlay-content-toggle';
        this.toggleBtn.textContent = '▶'; // Collapsed state (right arrow)
        this.toggleBtn.type = 'button';
        const headerTextSpan = document.createElement('span');
        headerTextSpan.className = 'overlay-content-header-text';
        headerTextSpan.textContent = 'Debug Options';
        this.headerDiv.appendChild(this.toggleBtn);
        this.headerDiv.appendChild(headerTextSpan);
        // Create content div (collapsed by default)
        this.contentDiv = document.createElement('div');
        this.contentDiv.className = 'content overlay overlay-debug-content';
        this.contentDiv.style.display = 'none'; // Start collapsed
        // Create table with 6 columns: Debug, Log, Blacklist, Graylist, Whitelist, Limit
        const debugTable = document.createElement('table');
        debugTable.className = 'overlay-debug-filter-table';
        // Header row
        const headerRow = document.createElement('tr');
        ['Debug', 'Log', 'Blacklist', 'Graylist', 'Whitelist', 'Limit'].forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            headerRow.appendChild(th);
        });
        debugTable.appendChild(headerRow);
        // Input row
        const inputRow = document.createElement('tr');
        // Debug checkbox cell
        const debugCell = document.createElement('td');
        this.debugCheckbox = document.createElement('input');
        this.debugCheckbox.type = 'checkbox';
        this.debugCheckbox.id = 'overlay-debug-checkbox';
        debugCell.appendChild(this.debugCheckbox);
        inputRow.appendChild(debugCell);
        // Log checkbox cell
        const logCell = document.createElement('td');
        this.logCheckbox = document.createElement('input');
        this.logCheckbox.type = 'checkbox';
        this.logCheckbox.id = 'overlay-log-checkbox';
        logCell.appendChild(this.logCheckbox);
        inputRow.appendChild(logCell);
        // Blacklist input
        const blackCell = document.createElement('td');
        this.blackInput = document.createElement('input');
        this.blackInput.type = 'text';
        this.blackInput.className = 'overlay-form-input';
        this.blackInput.placeholder = 'e.g., dispatch,get_arg';
        blackCell.appendChild(this.blackInput);
        inputRow.appendChild(blackCell);
        // Graylist input
        const grayCell = document.createElement('td');
        this.grayInput = document.createElement('input');
        this.grayInput.type = 'text';
        this.grayInput.className = 'overlay-form-input';
        this.grayInput.placeholder = 'e.g., response.py,gateway.py';
        grayCell.appendChild(this.grayInput);
        inputRow.appendChild(grayCell);
        // Whitelist input
        const whiteCell = document.createElement('td');
        this.whiteInput = document.createElement('input');
        this.whiteInput.type = 'text';
        this.whiteInput.className = 'overlay-form-input';
        this.whiteInput.placeholder = 'e.g., *gateway*';
        whiteCell.appendChild(this.whiteInput);
        inputRow.appendChild(whiteCell);
        // Debug limit input
        const limitCell = document.createElement('td');
        this.debugLimitInput = document.createElement('input');
        this.debugLimitInput.type = 'number';
        this.debugLimitInput.className = 'overlay-form-input';
        this.debugLimitInput.placeholder = 'e.g., 10';
        this.debugLimitInput.min = '0';
        limitCell.appendChild(this.debugLimitInput);
        inputRow.appendChild(limitCell);
        debugTable.appendChild(inputRow);
        this.contentDiv.appendChild(debugTable);
        // Add toggle functionality
        this.toggleBtn.addEventListener('click', () => {
            this.toggle();
        });
        // Assemble container
        this.container.appendChild(this.headerDiv);
        this.container.appendChild(this.contentDiv);
    }
    /**
     * Toggle expand/collapse state.
     */
    toggle() {
        this.isCollapsed = !this.isCollapsed;
        if (this.isCollapsed) {
            this.contentDiv.style.display = 'none';
            this.toggleBtn.textContent = '▶'; // Collapsed state
        }
        else {
            this.contentDiv.style.display = '';
            this.toggleBtn.textContent = '▼'; // Expanded state
        }
    }
    /**
     * Collapse the debug section.
     */
    collapse() {
        if (!this.isCollapsed) {
            this.toggle();
        }
    }
    /**
     * Expand the debug section.
     */
    expand() {
        if (this.isCollapsed) {
            this.toggle();
        }
    }
    /**
     * Get current debug options values.
     */
    getOptions() {
        const options = {
            debug: this.debugCheckbox.checked,
            log: this.logCheckbox.checked
        };
        if (this.debugCheckbox.checked) {
            if (this.whiteInput.value.trim()) {
                options.white = this.whiteInput.value.trim();
            }
            if (this.grayInput.value.trim()) {
                options.gray = this.grayInput.value.trim();
            }
            if (this.blackInput.value.trim()) {
                options.black = this.blackInput.value.trim();
            }
            if (this.debugLimitInput.value) {
                const limit = parseInt(this.debugLimitInput.value, 10);
                if (!isNaN(limit) && limit > 0) {
                    options.debugLimit = limit;
                }
            }
        }
        return options;
    }
    /**
     * Render the debug options component (returns the container with header and content).
     */
    render() {
        return this.container;
    }
}
