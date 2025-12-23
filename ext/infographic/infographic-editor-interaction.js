// Editor-only interaction functions (drag, grid, toggle controls)
// This file is only loaded in editor mode (HTML file), not deployed

function startDrag(nodeId, e) {
	// Don't start drag if modal is open or clicking a glossary link
	if (glossaryModalOpen || isClickingGlossaryLink) {
		return;
	}
	
	draggedNode = nodeId;
	const svgPoint = getSVGPoint(e);
	const pos = nodePositions[nodeId];
	// Use text starting position directly
	offset.x = svgPoint.x - pos.x;
	offset.y = svgPoint.y - pos.y;
	
	document.addEventListener('mousemove', drag);
	document.addEventListener('mouseup', stopDrag);
	e.preventDefault();
	e.stopPropagation();
}

function drag(e) {
	// Handle node dragging
	if (draggedNode && !glossaryModalOpen) {
		const svgPoint = getSVGPoint(e);
		const pos = nodePositions[draggedNode];
		// User is dragging text starting position
		let draggedTextX = svgPoint.x - offset.x;
		let draggedTextY = svgPoint.y - offset.y;
		
		// Snap to grid if enabled (snap text starting position)
		if (gridEnabled) {
			draggedTextX = Math.round(draggedTextX / gridSize) * gridSize;
			draggedTextY = Math.round(draggedTextY / gridSize) * gridSize;
		}
		
		// Save text starting position
		pos.x = draggedTextX;
		pos.y = draggedTextY;
		render();
		return;
	}
	
	// Handle connection box dragging
	if (draggedConnection && !glossaryModalOpen) {
		const svgPoint = getSVGPoint(e);
		const pos = connectionPositions[draggedConnection];
		// User is dragging text starting position
		let draggedTextX = svgPoint.x - offset.x;
		let draggedTextY = svgPoint.y - offset.y;
		
		// Snap to grid if enabled (snap text starting position)
		if (gridEnabled) {
			draggedTextX = Math.round(draggedTextX / gridSize) * gridSize;
			draggedTextY = Math.round(draggedTextY / gridSize) * gridSize;
		}
		
		// Save text starting position
		pos.x = draggedTextX;
		pos.y = draggedTextY;
		render();
		return;
	}
	
	stopDrag();
}

function stopDrag() {
	// Save positions to allPositions when dragging stops
	if (currentInfographicId) {
		if (!allPositions[currentInfographicId]) {
			allPositions[currentInfographicId] = {};
		}
		allPositions[currentInfographicId].nodes = { ...nodePositions };
		allPositions[currentInfographicId].connections = { ...connectionPositions };
	}
	
	draggedNode = null;
	draggedConnection = null;
	document.removeEventListener('mousemove', drag);
	document.removeEventListener('mouseup', stopDrag);
}

function startConnectionDrag(connId, e) {
	// Don't start drag if modal is open or clicking a glossary link
	if (glossaryModalOpen || isClickingGlossaryLink) {
		return;
	}
	
	draggedConnection = connId;
	const svgPoint = getSVGPoint(e);
	const pos = connectionPositions[connId];
	// Use text starting position directly
	offset.x = svgPoint.x - pos.x;
	offset.y = svgPoint.y - pos.y;
	
	document.addEventListener('mousemove', drag);
	document.addEventListener('mouseup', stopDrag);
	e.preventDefault();
	e.stopPropagation();
}

// Toggle controls panel visibility
function toggleControls() {
	const container = document.querySelector('.container');
	const toggleBtn = document.getElementById('toggleControlsBtn');
	
	if (!container) return;
	
	const isCollapsed = container.classList.contains('controls-collapsed');
	
	if (isCollapsed) {
		// Expand: remove collapsed class
		container.classList.remove('controls-collapsed');
		if (toggleBtn) {
			toggleBtn.textContent = '◀';
			toggleBtn.title = 'Collapse Controls';
		}
	} else {
		// Collapse: add collapsed class
		container.classList.add('controls-collapsed');
		if (toggleBtn) {
			toggleBtn.textContent = '▶';
			toggleBtn.title = 'Expand Controls';
		}
	}
	
	// Trigger a resize event and zoom to fit after transition completes
	setTimeout(() => {
		if (window.dispatchEvent) {
			window.dispatchEvent(new Event('resize'));
		}
		// Zoom to fit the new canvas size after sidebar collapse/expand
		zoomToFit();
	}, 300); // Wait for transition to complete
}

// Grid functions
function toggleGrid() {
	gridEnabled = !gridEnabled;
	const gridBtn = document.getElementById('gridToggleBtn');
	const increaseBtn = document.getElementById('increaseGridBtn');
	const decreaseBtn = document.getElementById('decreaseGridBtn');
	
	if (gridBtn) {
		gridBtn.textContent = gridEnabled ? '⬛' : '⬜';
		gridBtn.title = gridEnabled ? 'Disable Grid' : 'Enable Grid';
	}
	
	// Show/hide resolution controls
	if (increaseBtn) increaseBtn.style.display = gridEnabled ? 'flex' : 'none';
	if (decreaseBtn) decreaseBtn.style.display = gridEnabled ? 'flex' : 'none';
	
	render(); // Re-render to show/hide grid
}

function increaseGridResolution() {
	gridSize = Math.min(gridSize + 5, maxGridSize);
	if (gridEnabled) {
		render(); // Re-render to update grid
	}
}

function decreaseGridResolution() {
	gridSize = Math.max(gridSize - 5, minGridSize);
	if (gridEnabled) {
		render(); // Re-render to update grid
	}
}

