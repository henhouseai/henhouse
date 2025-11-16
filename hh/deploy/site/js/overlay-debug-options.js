/**
 * OverlayDebugOptions - Debug options UI component for overlay forms.
 * Provides checkboxes and input fields for debug/log flags and filters.
 */
export class OverlayDebugOptions {
    constructor() {
        this.whiteInput = null;
        this.grayInput = null;
        this.blackInput = null;
        this.debugLimitInput = null;
        this.container = document.createElement('div');
        this.container.className = 'overlay-debug-options';
        // Debug checkbox (enables everything)
        const debugLabel = document.createElement('label');
        debugLabel.className = 'overlay-label-inline';
        this.debugCheckbox = document.createElement('input');
        this.debugCheckbox.type = 'checkbox';
        this.debugCheckbox.id = 'overlay-debug-checkbox';
        this.debugCheckbox.addEventListener('change', () => this.updateVisibility());
        debugLabel.appendChild(this.debugCheckbox);
        debugLabel.appendChild(document.createTextNode(' Debug'));
        this.container.appendChild(debugLabel);
        // Log checkbox (enabled when debug is checked)
        const logLabel = document.createElement('label');
        logLabel.className = 'overlay-label-inline';
        this.logCheckbox = document.createElement('input');
        this.logCheckbox.type = 'checkbox';
        this.logCheckbox.id = 'overlay-log-checkbox';
        this.logCheckbox.disabled = true;
        this.logCheckbox.addEventListener('change', () => this.updateVisibility());
        logLabel.appendChild(this.logCheckbox);
        logLabel.appendChild(document.createTextNode(' Log'));
        this.container.appendChild(logLabel);
        // Filter options container (hidden by default, will be shown below header when debug is checked)
        const filterContainer = document.createElement('div');
        filterContainer.className = 'overlay-debug-filters';
        filterContainer.style.display = 'none';
        // White list input
        const whiteGroup = document.createElement('div');
        whiteGroup.className = 'overlay-form-group';
        const whiteLabel = document.createElement('label');
        whiteLabel.textContent = 'Whitelist:';
        this.whiteInput = document.createElement('input');
        this.whiteInput.type = 'text';
        this.whiteInput.className = 'overlay-form-input';
        this.whiteInput.placeholder = 'e.g., *gateway*';
        whiteGroup.appendChild(whiteLabel);
        whiteGroup.appendChild(this.whiteInput);
        filterContainer.appendChild(whiteGroup);
        // Gray list input
        const grayGroup = document.createElement('div');
        grayGroup.className = 'overlay-form-group';
        const grayLabel = document.createElement('label');
        grayLabel.textContent = 'Graylist:';
        this.grayInput = document.createElement('input');
        this.grayInput.type = 'text';
        this.grayInput.className = 'overlay-form-input';
        this.grayInput.placeholder = 'e.g., response.py,gateway.py';
        grayGroup.appendChild(grayLabel);
        grayGroup.appendChild(this.grayInput);
        filterContainer.appendChild(grayGroup);
        // Black list input
        const blackGroup = document.createElement('div');
        blackGroup.className = 'overlay-form-group';
        const blackLabel = document.createElement('label');
        blackLabel.textContent = 'Blacklist:';
        this.blackInput = document.createElement('input');
        this.blackInput.type = 'text';
        this.blackInput.className = 'overlay-form-input';
        this.blackInput.placeholder = 'e.g., dispatch,get_arg';
        blackGroup.appendChild(blackLabel);
        blackGroup.appendChild(this.blackInput);
        filterContainer.appendChild(blackGroup);
        // Debug limit input
        const limitGroup = document.createElement('div');
        limitGroup.className = 'overlay-form-group';
        const limitLabel = document.createElement('label');
        limitLabel.textContent = 'Debug Limit:';
        this.debugLimitInput = document.createElement('input');
        this.debugLimitInput.type = 'number';
        this.debugLimitInput.className = 'overlay-form-input';
        this.debugLimitInput.placeholder = 'e.g., 10';
        this.debugLimitInput.min = '0';
        limitGroup.appendChild(limitLabel);
        limitGroup.appendChild(this.debugLimitInput);
        filterContainer.appendChild(limitGroup);
        this.container.appendChild(filterContainer);
        // Store reference to filter container for visibility updates
        this.container._filterContainer = filterContainer;
    }
    /**
     * Update visibility of options based on checkbox states.
     */
    updateVisibility() {
        const filterContainer = this.container._filterContainer;
        if (this.debugCheckbox.checked) {
            // Enable log checkbox
            this.logCheckbox.disabled = false;
            // Show filter options as dropdown
            filterContainer.style.display = 'block';
        }
        else {
            // Disable log checkbox and uncheck it
            this.logCheckbox.disabled = true;
            this.logCheckbox.checked = false;
            // Hide filter options
            filterContainer.style.display = 'none';
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
            if (this.whiteInput && this.whiteInput.value.trim()) {
                options.white = this.whiteInput.value.trim();
            }
            if (this.grayInput && this.grayInput.value.trim()) {
                options.gray = this.grayInput.value.trim();
            }
            if (this.blackInput && this.blackInput.value.trim()) {
                options.black = this.blackInput.value.trim();
            }
            if (this.debugLimitInput && this.debugLimitInput.value) {
                const limit = parseInt(this.debugLimitInput.value, 10);
                if (!isNaN(limit) && limit > 0) {
                    options.debugLimit = limit;
                }
            }
        }
        return options;
    }
    /**
     * Render the debug options component.
     */
    render() {
        return this.container;
    }
}
