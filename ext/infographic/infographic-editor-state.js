// Editor-only state (grid and drag state)
// This file is only loaded in editor mode (HTML file), not deployed

// Grid state
let gridEnabled = false;
let gridSize = 20; // Default grid spacing in pixels
let minGridSize = 5;
let maxGridSize = 100;

// Grid drawing state variables (used by drawGrid function)
let gridMinX, gridMinY, gridMaxX, gridMaxY;

