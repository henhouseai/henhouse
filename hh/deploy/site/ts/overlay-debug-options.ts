/**
 * OverlayDebugOptions - Debug options UI component for overlay forms.
 * Provides checkboxes and input fields for debug/log flags and filters.
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
  private filterContainer: HTMLElement;
  private debugCheckbox: HTMLInputElement;
  private logCheckbox: HTMLInputElement;
  private whiteInput: HTMLInputElement | null = null;
  private grayInput: HTMLInputElement | null = null;
  private blackInput: HTMLInputElement | null = null;
  private debugLimitInput: HTMLInputElement | null = null;
  private isVisible: boolean = true; // Track visibility state

  constructor() {
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
    
    // Log checkbox (only appears when debug is checked)
    const logLabel = document.createElement('label');
    logLabel.className = 'overlay-label-inline';
    logLabel.style.display = 'none';
    this.logCheckbox = document.createElement('input');
    this.logCheckbox.type = 'checkbox';
    this.logCheckbox.id = 'overlay-log-checkbox';
    this.logCheckbox.addEventListener('change', () => this.updateVisibility());
    
    logLabel.appendChild(this.logCheckbox);
    logLabel.appendChild(document.createTextNode(' Log'));
    this.container.appendChild(logLabel);
    
    // Store reference to log label for visibility updates
    (this.container as any)._logLabel = logLabel;
    
    // Filter options container (will be placed after header, before content)
    this.filterContainer = document.createElement('div');
    this.filterContainer.className = 'overlayContent overlay-debug-filters';
    this.filterContainer.style.display = 'none';
    
    // Create table for filter inputs (2 rows, 4 columns)
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
    this.filterContainer.appendChild(filterTable);
  }

  /**
   * Update visibility of options based on checkbox states.
   */
  private updateVisibility(): void {
    const logLabel = (this.container as any)._logLabel as HTMLElement;
    
    if (this.debugCheckbox.checked) {
      // Show log checkbox
      logLabel.style.display = 'inline-flex';
      // Show filter options
      this.filterContainer.style.display = 'block';
    } else {
      // Hide log checkbox and uncheck it
      logLabel.style.display = 'none';
      this.logCheckbox.checked = false;
      // Hide filter options
      this.filterContainer.style.display = 'none';
    }
  }

  /**
   * Get current debug options values (reads from DOM, so must be called before hiding).
   */
  getOptionsBeforeHide(): DebugOptions {
    // Read values before hiding - this preserves the state
    return this.getOptions();
  }

  /**
   * Hide filters and uncheck boxes (for loading state).
   * Preserves input values but unchecks boxes.
   * NOTE: Call getOptionsBeforeHide() first if you need the checkbox states!
   */
  hideForLoading(): void {
    this.debugCheckbox.checked = false;
    this.logCheckbox.checked = false;
    const logLabel = (this.container as any)._logLabel as HTMLElement;
    logLabel.style.display = 'none';
    this.filterContainer.style.display = 'none';
  }

  /**
   * Show filters and checkboxes again (for error state).
   * Restores input values that were preserved.
   */
  showForError(): void {
    // Checkboxes remain unchecked, but filters are visible again
    this.filterContainer.style.display = 'block';
  }

  /**
   * Get the filter container element (for placement in content area).
   */
  getFilterContainer(): HTMLElement {
    return this.filterContainer;
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
   * Show the debug options component.
   */
  show(): void {
    this.isVisible = true;
    this.container.style.display = '';
  }

  /**
   * Hide the debug options component.
   */
  hide(): void {
    this.isVisible = false;
    this.container.style.display = 'none';
    // Also hide filter container when hiding debug options
    this.filterContainer.style.display = 'none';
  }

  /**
   * Check if debug options are visible.
   */
  getVisible(): boolean {
    return this.isVisible;
  }

  /**
   * Render the debug options component.
   */
  render(): HTMLElement {
    return this.container;
  }
}

