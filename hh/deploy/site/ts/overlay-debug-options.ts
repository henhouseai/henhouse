/**
 * OverlayDebugOptions - Debug options UI component for overlay forms.
 * Provides a collapsible footer section with debug/log checkboxes and filter inputs.
 */

export interface DebugOptions {
  debug: boolean;
  log: boolean;
  white?: string;
  gray?: string;
  black?: string;
  debugLimit?: number;
}

export class OverlayDebugOptions {
  private container: HTMLElement;
  private headerDiv: HTMLElement;
  private contentDiv: HTMLElement;
  private toggleBtn: HTMLButtonElement;
  private debugCheckbox: HTMLInputElement;
  private logCheckbox: HTMLInputElement;
  private whiteInput: HTMLInputElement;
  private grayInput: HTMLInputElement;
  private blackInput: HTMLInputElement;
  private debugLimitInput: HTMLInputElement;
  private isCollapsed: boolean = true; // Start collapsed by default

  constructor() {
    // Create container for the entire debug section
    this.container = document.createElement('div');
    this.container.className = 'overlay-debug-section';
    
    // Create header with expand/collapse button
    this.headerDiv = document.createElement('div');
    this.headerDiv.className = 'overlayContentHeader';
    
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
    this.contentDiv.className = 'overlayContent overlay-debug-content';
    this.contentDiv.style.display = 'none'; // Start collapsed
    
    // Create inner container for checkboxes and table
    const innerContainer = document.createElement('div');
    innerContainer.className = 'overlay-debug-options-inner';
    
    // Checkboxes container
    const checkboxesDiv = document.createElement('div');
    checkboxesDiv.className = 'overlay-debug-checkboxes';
    
    // Debug checkbox
    const debugLabel = document.createElement('label');
    debugLabel.className = 'overlay-label-inline';
    this.debugCheckbox = document.createElement('input');
    this.debugCheckbox.type = 'checkbox';
    this.debugCheckbox.id = 'overlay-debug-checkbox';
    debugLabel.appendChild(this.debugCheckbox);
    debugLabel.appendChild(document.createTextNode(' Debug'));
    checkboxesDiv.appendChild(debugLabel);
    
    // Log checkbox
    const logLabel = document.createElement('label');
    logLabel.className = 'overlay-label-inline';
    this.logCheckbox = document.createElement('input');
    this.logCheckbox.type = 'checkbox';
    this.logCheckbox.id = 'overlay-log-checkbox';
    logLabel.appendChild(this.logCheckbox);
    logLabel.appendChild(document.createTextNode(' Log'));
    checkboxesDiv.appendChild(logLabel);
    
    innerContainer.appendChild(checkboxesDiv);
    
    // Filter table
    const filterTable = document.createElement('table');
    filterTable.className = 'overlay-debug-filter-table';
    
    // Header row
    const headerRow = document.createElement('tr');
    ['Blacklist', 'Graylist', 'Whitelist', 'Limit'].forEach(text => {
      const th = document.createElement('th');
      th.textContent = text;
      headerRow.appendChild(th);
    });
    filterTable.appendChild(headerRow);
    
    // Input row
    const inputRow = document.createElement('tr');
    
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
    
    filterTable.appendChild(inputRow);
    innerContainer.appendChild(filterTable);
    
    this.contentDiv.appendChild(innerContainer);
    
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
  toggle(): void {
    this.isCollapsed = !this.isCollapsed;
    if (this.isCollapsed) {
      this.contentDiv.style.display = 'none';
      this.toggleBtn.textContent = '▶'; // Collapsed state
    } else {
      this.contentDiv.style.display = '';
      this.toggleBtn.textContent = '▼'; // Expanded state
    }
  }

  /**
   * Collapse the debug section.
   */
  collapse(): void {
    if (!this.isCollapsed) {
      this.toggle();
    }
  }

  /**
   * Expand the debug section.
   */
  expand(): void {
    if (this.isCollapsed) {
      this.toggle();
    }
  }

  /**
   * Get current debug options values.
   */
  getOptions(): DebugOptions {
    const options: DebugOptions = {
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
  render(): HTMLElement {
    return this.container;
  }
}
