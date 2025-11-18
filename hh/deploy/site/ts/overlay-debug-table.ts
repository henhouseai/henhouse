/**
 * OverlayDebugTable - Renders debug output as a table in overlay forms.
 * Parses JSON debug entries and builds a table similar to the debug_table system.
 */

export interface DebugEntry {
  L: string;  // level (trace_in, trace_out, log, debug, warn)
  F: string;  // folder/module
  I: string;  // filename
  U: string;  // function
  M: string;  // message
  T: number;  // timestamp delta (seconds)
}

export interface DebugData {
  entries: DebugEntry[];
}

// Color names matching the Python COLOR_NAMES list
const COLOR_NAMES = [
  'red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'magenta', 'gold',
  'white', 'brown', 'pink', 'pastel_yellow', 'pastel_cyan', 'pastel_pink',
  'pastel_green', 'pastel_blue', 'pastel_purple', 'pastel_orange', 'pastel_red',
  'pastel_lavender', 'pastel_peach', 'pastel_mint', 'pastel_lilac', 'pastel_sky',
  'pastel_rose', 'pastel_aqua', 'pastel_coral', 'pastel_lime', 'pastel_violet'
];

export class OverlayDebugTable {
  private moduleColors: Map<string, number> = new Map();
  private filenameColors: Map<string, number> = new Map();
  private functionColors: Map<string, number> = new Map();
  private moduleColorIndex: number = 0;

  /**
   * Get color index for a module (round-robin assignment).
   */
  private getModuleColorIndex(module: string): number {
    if (!this.moduleColors.has(module)) {
      this.moduleColors.set(module, this.moduleColorIndex);
      this.moduleColorIndex = (this.moduleColorIndex + 1) % COLOR_NAMES.length;
    }
    return this.moduleColors.get(module)!;
  }

  /**
   * Get color index for a filename (based on module color).
   */
  private getFilenameColorIndex(module: string, filename: string): number {
    const key = `${module}:${filename}`;
    if (!this.filenameColors.has(key)) {
      const moduleColorIndex = this.getModuleColorIndex(module);
      const moduleFilenames = Array.from(this.filenameColors.keys())
        .filter(k => k.startsWith(`${module}:`))
        .map(k => k.split(':')[1]);
      const colorIndex = (moduleColorIndex + moduleFilenames.length) % COLOR_NAMES.length;
      this.filenameColors.set(key, colorIndex);
    }
    return this.filenameColors.get(key)!;
  }

  /**
   * Get color index for a function (based on filename color).
   */
  private getFunctionColorIndex(module: string, filename: string, functionName: string): number {
    const key = `${module}:${filename}:${functionName}`;
    if (!this.functionColors.has(key)) {
      const filenameColorIndex = this.getFilenameColorIndex(module, filename);
      const filenameFunctions = Array.from(this.functionColors.keys())
        .filter(k => k.startsWith(`${module}:${filename}:`))
        .map(k => k.split(':')[2]);
      const colorIndex = (filenameColorIndex + filenameFunctions.length) % COLOR_NAMES.length;
      this.functionColors.set(key, colorIndex);
    }
    return this.functionColors.get(key)!;
  }

  /**
   * Get CSS class name for a color index.
   */
  private getColorClass(colorIndex: number): string {
    const colorName = COLOR_NAMES[colorIndex];
    // Convert snake_case to kebab-case for CSS classes
    return `color-${colorName.replace(/_/g, '-')}`;
  }

  /**
   * Format timestamp delta as string.
   */
  private formatTimestamp(delta: number): string {
    return `+${delta.toFixed(3)}s`;
  }

  /**
   * Get level display text and CSS class.
   */
  private getLevelInfo(level: string): { text: string; class: string } {
    switch (level) {
      case 'trace_in':
        return { text: '→', class: 'debug-level-trace-in' };
      case 'trace_out':
        return { text: '←', class: 'debug-level-trace-out' };
      case 'log':
        return { text: 'LOG', class: 'debug-level-log' };
      case 'debug':
        return { text: 'DBG', class: 'debug-level-debug' };
      case 'warn':
        return { text: 'WRN', class: 'debug-level-warn' };
      default:
        return { text: level.toUpperCase(), class: 'debug-level-unknown' };
    }
  }

  /**
   * Render debug table from JSON debug data.
   */
  render(debugData: DebugData): HTMLElement {
    if (!debugData.entries || debugData.entries.length === 0) {
      const emptyMsg = document.createElement('div');
      emptyMsg.className = 'overlay-debug-empty';
      emptyMsg.textContent = 'No debug entries';
      return emptyMsg;
    }

    // Create table
    const table = document.createElement('table');
    table.className = 'overlay-debug-table';

    // Create header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    ['Time', 'Level', 'Module', 'File', 'Function', 'Message'].forEach(text => {
      const th = document.createElement('th');
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create body
    const tbody = document.createElement('tbody');
    debugData.entries.forEach((entry, index) => {
      const row = document.createElement('tr');
      if (index % 2 === 0) {
        row.classList.add('even');
      }

      // Time column
      const timeCell = document.createElement('td');
      timeCell.className = 'debug-time';
      timeCell.textContent = this.formatTimestamp(entry.T);
      row.appendChild(timeCell);

      // Level column
      const levelCell = document.createElement('td');
      const levelInfo = this.getLevelInfo(entry.L);
      levelCell.className = `debug-level ${levelInfo.class}`;
      levelCell.textContent = levelInfo.text;
      row.appendChild(levelCell);

      // Module column (with color)
      const moduleCell = document.createElement('td');
      moduleCell.className = `debug-module ${this.getColorClass(this.getModuleColorIndex(entry.F))}`;
      moduleCell.textContent = entry.F;
      row.appendChild(moduleCell);

      // File column (with color)
      const fileCell = document.createElement('td');
      fileCell.className = `debug-file ${this.getColorClass(this.getFilenameColorIndex(entry.F, entry.I))}`;
      fileCell.textContent = entry.I;
      row.appendChild(fileCell);

      // Function column (with color)
      const funcCell = document.createElement('td');
      funcCell.className = `debug-function ${this.getColorClass(this.getFunctionColorIndex(entry.F, entry.I, entry.U))}`;
      funcCell.textContent = entry.U;
      row.appendChild(funcCell);

      // Message column
      const msgCell = document.createElement('td');
      msgCell.className = 'debug-message';
      msgCell.textContent = entry.M;
      row.appendChild(msgCell);

      tbody.appendChild(row);
    });
    table.appendChild(tbody);

    return table;
  }
}

