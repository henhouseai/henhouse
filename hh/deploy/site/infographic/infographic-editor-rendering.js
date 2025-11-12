// Editor-only rendering functions (grid drawing)
// This file is only loaded in editor mode (HTML file), not deployed

function drawGrid() {
	if (!svgGroup || !canvas) return;
	
	// Calculate actual bounds of all content (like zoomToFit does)
	let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
	
	// Check all nodes
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
	
	// Check all connection boxes
	connections.forEach(conn => {
		const connId = `${conn.from}->${conn.to}`;
		const pos = connectionPositions[connId];
		if (!pos) return;
		const textStartPos = pos;
		const boxCenterY = textStartPos.y + (textStartPos.boxOffsetY || 0);
		const boxWidth = textStartPos.boxWidth || 200;
		const boxHeight = textStartPos.boxHeight || 50;
		const boxX = textStartPos.x - (boxWidth / 2);
		const boxY = boxCenterY - (boxHeight / 2);
		minX = Math.min(minX, boxX);
		minY = Math.min(minY, boxY);
		maxX = Math.max(maxX, boxX + boxWidth);
		maxY = Math.max(maxY, boxY + boxHeight);
	});
	
	// If no content found, use canvas size
	if (minX === Infinity) {
		minX = 0;
		minY = 0;
		maxX = canvas.clientWidth || 2000;
		maxY = canvas.clientHeight || 2000;
	}
	
	// Find center of content
	const centerX = (minX + maxX) / 2;
	const centerY = (minY + maxY) / 2;
	
	// Round center to nearest red line intersection (every 10 grid units)
	const redLineSpacing = gridSize * 10;
	const alignedCenterX = Math.round(centerX / redLineSpacing) * redLineSpacing;
	const alignedCenterY = Math.round(centerY / redLineSpacing) * redLineSpacing;
	
	// Add padding: 1-2 red lines worth (10-20 grid units)
	const padding = gridSize * 15; // ~1.5 red lines
	const contentWidth = maxX - minX;
	const contentHeight = maxY - minY;
	
	// Make grid area a multiple of 20 grid units (2 red line spacings) to ensure alignment
	const minGridWidth = contentWidth + (padding * 2);
	const minGridHeight = contentHeight + (padding * 2);
	const alignedGridWidth = Math.ceil(minGridWidth / (20 * gridSize)) * (20 * gridSize);
	const alignedGridHeight = Math.ceil(minGridHeight / (20 * gridSize)) * (20 * gridSize);
	
	// Center the aligned grid area on the aligned center (red line intersection)
	gridMinX = alignedCenterX - alignedGridWidth / 2;
	gridMinY = alignedCenterY - alignedGridHeight / 2;
	gridMaxX = alignedCenterX + alignedGridWidth / 2;
	gridMaxY = alignedCenterY + alignedGridHeight / 2;
	
	// Create grid group
	const gridGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
	gridGroup.setAttribute('id', 'grid');
	gridGroup.setAttribute('opacity', '0.3');
	
	// Draw vertical lines (starting from gridMinX, aligned to gridSize)
	let verticalIndex = 0;
	const startX = Math.floor(gridMinX / gridSize) * gridSize;
	for (let x = startX; x <= gridMaxX; x += gridSize) {
		const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
		line.setAttribute('x1', x);
		line.setAttribute('y1', gridMinY);
		line.setAttribute('x2', x);
		line.setAttribute('y2', gridMaxY);
		// Every 10th line is red, others are blue
		const isTenth = (verticalIndex % 10 === 0);
		line.setAttribute('stroke', isTenth ? '#ff4444' : '#79c0ff');
		line.setAttribute('stroke-width', isTenth ? '1' : '0.5');
		gridGroup.appendChild(line);
		verticalIndex++;
	}
	
	// Draw horizontal lines (starting from gridMinY, aligned to gridSize)
	let horizontalIndex = 0;
	const startY = Math.floor(gridMinY / gridSize) * gridSize;
	for (let y = startY; y <= gridMaxY; y += gridSize) {
		const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
		line.setAttribute('x1', gridMinX);
		line.setAttribute('y1', y);
		line.setAttribute('x2', gridMaxX);
		line.setAttribute('y2', y);
		// Every 10th line is red, others are blue
		const isTenth = (horizontalIndex % 10 === 0);
		line.setAttribute('stroke', isTenth ? '#ff4444' : '#79c0ff');
		line.setAttribute('stroke-width', isTenth ? '1' : '0.5');
		gridGroup.appendChild(line);
		horizontalIndex++;
	}
	
	// Insert grid at the beginning (behind everything)
	const defs = svgGroup.querySelector('defs');
	if (defs) {
		svgGroup.insertBefore(gridGroup, defs.nextSibling);
	} else {
		svgGroup.insertBefore(gridGroup, svgGroup.firstChild);
	}
}

