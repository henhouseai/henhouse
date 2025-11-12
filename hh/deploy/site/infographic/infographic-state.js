// Global state management
let glossary = {};
let allInfographics = [];
let currentInfographicId = null;
let nodes = [];
let connections = [];
let draggedNode = null;
let draggedConnection = null; // Track which connection box is being dragged
let offset = { x: 0, y: 0 };
let nodePositions = {};
let connectionPositions = {}; // Store connection box positions: { connId: {x, y} }
let allPositions = {}; // Store positions per infographic: { infographicId: { nodeId: {x, y}, connections: { connId: {x, y} } } }
let glossaryModalOpen = false; // Track if glossary modal is open
let isClickingGlossaryLink = false; // Track if user is clicking a glossary link

// Panning state
let isPanning = false;
let panStart = { x: 0, y: 0 };
let panOffset = { x: 0, y: 0 };

// Zoom state
let zoomLevel = 1.0;
let minZoom = 0.25;
let maxZoom = 4.0;
let zoomStep = 0.25;

// Pinch-to-zoom state
let pinchStartDistance = 0;
let pinchStartZoom = 1.0;
let pinchCenter = { x: 0, y: 0 };

let canvas;
let canvasContainer;
let svgGroup; // Transform group for panning and zooming

