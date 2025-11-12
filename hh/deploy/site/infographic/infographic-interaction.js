// Core interaction handlers (pan, zoom - used by both deploy and editor)

function getSVGPoint(e) {
	if (!canvas) return { x: 0, y: 0 };
	const rect = canvas.getBoundingClientRect();
	// Account for pan offset and zoom when converting to SVG coordinates
	return {
		x: ((e.clientX - rect.left) - panOffset.x) / zoomLevel,
		y: ((e.clientY - rect.top) - panOffset.y) / zoomLevel
	};
}

function getScreenPoint(e) {
	if (!canvas) return { x: 0, y: 0 };
	const rect = canvas.getBoundingClientRect();
	return {
		x: e.clientX - rect.left,
		y: e.clientY - rect.top
	};
}

// Panning handlers
function startPan(e) {
	// Don't start pan if modal is open or clicking a glossary link
	// In editor mode, also check if dragging a node (handled by editor-interaction.js)
	if (glossaryModalOpen || isClickingGlossaryLink || (typeof draggedNode !== 'undefined' && draggedNode)) {
		return;
	}
	
	isPanning = true;
	const screenPoint = getScreenPoint(e);
	panStart.x = screenPoint.x - panOffset.x;
	panStart.y = screenPoint.y - panOffset.y;
	
	// Prevent default to avoid text selection and scrolling
	e.preventDefault();
	e.stopPropagation();
	
	// Change cursor
	if (canvas) {
		canvas.style.cursor = 'grabbing';
	}
}

function pan(e) {
	if (!isPanning || glossaryModalOpen) {
		return;
	}
	
	const screenPoint = getScreenPoint(e);
	panOffset.x = screenPoint.x - panStart.x;
	panOffset.y = screenPoint.y - panStart.y;
	
	applyPanTransform();
}

function stopPan() {
	isPanning = false;
	if (canvas) {
		canvas.style.cursor = 'move';
	}
}

function applyPanTransform() {
	if (!svgGroup) return;
	// Apply both pan and zoom transforms
	// Transform order: translate to center, scale, translate back, then pan
	const transform = `translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`;
	svgGroup.setAttribute('transform', transform);
}

// Zoom functions
function zoomIn() {
	if (zoomLevel < maxZoom) {
		zoomLevel = Math.min(zoomLevel + zoomStep, maxZoom);
		applyPanTransform();
	}
}

function zoomOut() {
	if (zoomLevel > minZoom) {
		zoomLevel = Math.max(zoomLevel - zoomStep, minZoom);
		applyPanTransform();
	}
}

function zoomToFit() {
	if (!canvas || nodes.length === 0) return;
	
	// Calculate bounding box of all nodes
	let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
	
	nodes.forEach(node => {
		const pos = nodePositions[node.id];
		if (!pos) return;
		
		const bounds = getNodeBounds(node.id);
		if (!bounds) return;
		
		minX = Math.min(minX, bounds.x);
		minY = Math.min(minY, bounds.y);
		maxX = Math.max(maxX, bounds.x + bounds.width);
		maxY = Math.max(maxY, bounds.y + bounds.height);
	});
	
	if (minX === Infinity) return;
	
	// Add padding
	const padding = 50;
	minX -= padding;
	minY -= padding;
	maxX += padding;
	maxY += padding;
	
	const contentWidth = maxX - minX;
	const contentHeight = maxY - minY;
	
	const canvasWidth = canvas.clientWidth;
	const canvasHeight = canvas.clientHeight;
	
	// Calculate zoom to fit
	const zoomX = canvasWidth / contentWidth;
	const zoomY = canvasHeight / contentHeight;
	zoomLevel = Math.min(zoomX, zoomY, maxZoom);
	zoomLevel = Math.max(zoomLevel, minZoom);
	
	// Center the content
	const centerX = (minX + maxX) / 2;
	const centerY = (minY + maxY) / 2;
	
	panOffset.x = canvasWidth / 2 - centerX * zoomLevel;
	panOffset.y = canvasHeight / 2 - centerY * zoomLevel;
	
	applyPanTransform();
}

// Helper function to calculate distance between two touch points
function getTouchDistance(touch1, touch2) {
	const dx = touch2.clientX - touch1.clientX;
	const dy = touch2.clientY - touch1.clientY;
	return Math.sqrt(dx * dx + dy * dy);
}

// Helper function to get center point between two touches
function getTouchCenter(touch1, touch2) {
	return {
		x: (touch1.clientX + touch2.clientX) / 2,
		y: (touch1.clientY + touch2.clientY) / 2
	};
}

// Touch event handlers for mobile
function handleTouchStart(e) {
	if (e.touches.length === 2) {
		// Two touches - start pinch-to-zoom
		const touch1 = e.touches[0];
		const touch2 = e.touches[1];
		pinchStartDistance = getTouchDistance(touch1, touch2);
		pinchStartZoom = zoomLevel;
		
		// Get the initial pinch center in screen coordinates (relative to canvas)
		const initialCenter = getTouchCenter(touch1, touch2);
		const rect = canvas.getBoundingClientRect();
		const initialCenterX = initialCenter.x - rect.left;
		const initialCenterY = initialCenter.y - rect.top;
		
		// Store the initial pinch center and pan offset
		pinchCenter = {
			x: initialCenterX,
			y: initialCenterY,
			startPanX: panOffset.x,
			startPanY: panOffset.y
		};
		
		// Stop any active panning or dragging
		stopPan();
		if (typeof stopDrag === 'function') {
			stopDrag();
		}
		e.preventDefault();
	} else if (e.touches.length === 1 && (typeof draggedNode === 'undefined' || !draggedNode)) {
		// Single touch - check if it's on a node or empty canvas
		const touch = e.touches[0];
		// Get the element at touch point
		const elementAtPoint = document.elementFromPoint(touch.clientX, touch.clientY);
		
		// Check if touch is on a node rectangle (node rectangles have fill="#1a4d2a")
		// Walk up the DOM tree to find if we're inside a node group
		let isOnNode = false;
		let current = elementAtPoint;
		while (current && current !== canvas) {
			if (current.tagName === 'rect' && current.getAttribute('fill') === '#1a4d2a') {
				isOnNode = true;
				break;
			}
			current = current.parentElement || current.parentNode;
		}
		
		// If touch is NOT on a node (on canvas background or SVG root), start panning
		if (!isOnNode && (elementAtPoint === canvas || elementAtPoint === svgGroup || 
		    (elementAtPoint && (elementAtPoint.tagName === 'svg' || elementAtPoint === canvasContainer)))) {
			startPan({ clientX: touch.clientX, clientY: touch.clientY });
		}
	}
}

function handleTouchMove(e) {
	if (e.touches.length === 2) {
		// Pinch-to-zoom
		const touch1 = e.touches[0];
		const touch2 = e.touches[1];
		const currentDistance = getTouchDistance(touch1, touch2);
		
		if (pinchStartDistance > 0 && pinchCenter.x !== undefined && pinchCenter.startPanX !== undefined) {
			// Calculate zoom scale based on distance change
			const scale = currentDistance / pinchStartDistance;
			const newZoom = pinchStartZoom * scale;
			
			// Clamp zoom to min/max
			zoomLevel = Math.max(minZoom, Math.min(maxZoom, newZoom));
			
			// Get current pinch center in screen coordinates
			const currentCenterScreen = getTouchCenter(touch1, touch2);
			const rect = canvas.getBoundingClientRect();
			const currentCenterX = currentCenterScreen.x - rect.left;
			const currentCenterY = currentCenterScreen.y - rect.top;
			
			// To zoom around the current pinch center point, we need:
			// The world point under current center should stay at current center
			// Formula: newPan = currentCenter * (1 - newZoom/oldZoom) + oldPan * (newZoom/oldZoom)
			const zoomRatio = zoomLevel / pinchStartZoom;
			panOffset.x = currentCenterX * (1 - zoomRatio) + pinchCenter.startPanX * zoomRatio;
			panOffset.y = currentCenterY * (1 - zoomRatio) + pinchCenter.startPanY * zoomRatio;
			
			applyPanTransform();
		}
		e.preventDefault();
	} else if (e.touches.length === 1) {
		if (isPanning) {
			const touch = e.touches[0];
			pan({ clientX: touch.clientX, clientY: touch.clientY });
			e.preventDefault();
		} else if ((typeof draggedNode !== 'undefined' && draggedNode) || (typeof draggedConnection !== 'undefined' && draggedConnection)) {
			// Continue node or connection drag (editor mode only)
			const touch = e.touches[0];
			if (typeof drag === 'function') {
				drag({ clientX: touch.clientX, clientY: touch.clientY });
			}
			e.preventDefault();
		}
	}
}

function handleTouchEnd(e) {
	if (e.touches.length === 0) {
		// Reset pinch state
		pinchStartDistance = 0;
		pinchCenter = { x: 0, y: 0 };
		stopPan();
		if (typeof stopDrag === 'function') {
			stopDrag();
		}
	} else if (e.touches.length === 1) {
		// Went from 2 touches to 1 - reset pinch and allow pan/drag
		pinchStartDistance = 0;
		pinchCenter = { x: 0, y: 0 };
	}
}

// Initialize panning event listeners
function initializePanning() {
	if (!canvas) return;
	
	// Mouse events for desktop
	canvas.addEventListener('mousedown', (e) => {
		const target = e.target;
		
		// Check if clicking on a glossary link (text with data-glossary-term attribute)
		const isGlossaryLink = target.tagName === 'text' && target.hasAttribute && target.hasAttribute('data-glossary-term');
		
		// Check if we're in editor mode (has drag functions)
		const isEditorMode = typeof startDrag === 'function';
		
		if (isEditorMode) {
			// Editor mode: only pan on canvas background (not boxes/text)
			const isNodeRect = target.tagName === 'rect' && target.getAttribute('fill') === '#1a4d2a';
			const isConnRect = target.tagName === 'rect' && target.getAttribute('fill') === '#1a3a6b';
			const isText = target.tagName === 'text';
			
			// If clicking directly on canvas/SVG or on defs/markers (arrow markers), start panning
			if ((target === canvas || target.tagName === 'svg' || 
			     (target.tagName === 'defs') || (target.parentElement && target.parentElement.tagName === 'defs')) &&
			    !isNodeRect && !isConnRect && !isText && !isGlossaryLink) {
				startPan(e);
			}
		} else {
			// Deploy mode: pan everywhere except glossary links
			if (!isGlossaryLink) {
				startPan(e);
			}
		}
	});
	
	document.addEventListener('mousemove', (e) => {
		if (isPanning) {
			pan(e);
		}
	});
	
	document.addEventListener('mouseup', (e) => {
		if (isPanning) {
			stopPan();
		}
	});
	
	// Touch events for mobile
	canvas.addEventListener('touchstart', handleTouchStart, { passive: false });
	canvas.addEventListener('touchmove', handleTouchMove, { passive: false });
	canvas.addEventListener('touchend', handleTouchEnd);
	canvas.addEventListener('touchcancel', handleTouchEnd);
	
	// Mouse wheel zoom for desktop (only if not a touch device)
	if (!('ontouchstart' in window) && navigator.maxTouchPoints === 0) {
		canvas.addEventListener('wheel', handleWheelZoom, { passive: false });
	}
	
	// Set initial cursor
	canvas.style.cursor = 'move';
}

// Mouse wheel zoom handler
function handleWheelZoom(e) {
	// Prevent page scrolling
	e.preventDefault();
	
	// Calculate zoom delta (negative delta = zoom in, positive = zoom out)
	const delta = e.deltaY;
	const zoomFactor = 0.1; // How much to zoom per wheel tick
	const zoomDelta = delta > 0 ? -zoomFactor : zoomFactor;
	
	// Get cursor position relative to canvas
	const rect = canvas.getBoundingClientRect();
	const cursorX = e.clientX - rect.left;
	const cursorY = e.clientY - rect.top;
	
	// Store old zoom and pan
	const oldZoom = zoomLevel;
	const oldPanX = panOffset.x;
	const oldPanY = panOffset.y;
	
	// Calculate new zoom
	const newZoom = Math.max(minZoom, Math.min(maxZoom, zoomLevel + zoomDelta * zoomLevel));
	
	// Only update if zoom actually changed
	if (newZoom !== oldZoom) {
		zoomLevel = newZoom;
		
		// Zoom around cursor position
		// Formula: newPan = cursorPos * (1 - newZoom/oldZoom) + oldPan * (newZoom/oldZoom)
		const zoomRatio = zoomLevel / oldZoom;
		panOffset.x = cursorX * (1 - zoomRatio) + oldPanX * zoomRatio;
		panOffset.y = cursorY * (1 - zoomRatio) + oldPanY * zoomRatio;
		
		applyPanTransform();
	}
}

// Update zoom controls visibility based on device type
function updateZoomControlsVisibility() {
	const zoomControls = document.querySelector('.zoom-controls');
	if (!zoomControls) return;
	
	// Check if device has touch capability
	const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
	
	// Show on desktop, hide on touch devices
	if (hasTouch) {
		zoomControls.style.display = 'none';
	} else {
		zoomControls.style.display = 'flex';
	}
}

