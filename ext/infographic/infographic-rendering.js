// Rendering functions for SVG canvas

function measureTextWidth(text, fontSize, fontWeight = 'normal') {
	if (!canvas) return 100; // Fallback width if canvas not ready
	// Create temporary text element to measure actual width
	const tempText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
	tempText.setAttribute('font-size', fontSize);
	tempText.setAttribute('font-weight', fontWeight);
	tempText.setAttribute('font-family', 'Arial, sans-serif');
	tempText.textContent = text;
	tempText.style.visibility = 'hidden';
	canvas.appendChild(tempText);
	const bbox = tempText.getBBox();
	canvas.removeChild(tempText);
	return bbox.width;
}

// Measure actual width of multiple text elements that will be rendered side-by-side
function measureTextElementsWidth(elements) {
	if (!canvas || !elements || elements.length === 0) return 0;
	
	// Create a temporary group to measure all elements together
	const tempGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
	tempGroup.style.visibility = 'hidden';
	
	let currentX = 0;
	let maxWidth = 0;
	
	elements.forEach(({ text, fontSize, fontWeight }) => {
		const tempText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
		tempText.setAttribute('font-size', fontSize || '9px');
		tempText.setAttribute('font-weight', fontWeight || 'normal');
		tempText.setAttribute('font-family', 'Arial, sans-serif');
		tempText.setAttribute('x', currentX);
		tempText.setAttribute('y', 0);
		tempText.textContent = text;
		tempGroup.appendChild(tempText);
		
		// Measure this element
		canvas.appendChild(tempGroup);
		const bbox = tempText.getBBox();
		canvas.removeChild(tempGroup);
		
		currentX += bbox.width;
		maxWidth = currentX;
	});
	
	return maxWidth;
}

function getNodeBounds(nodeId) {
	// Calculate the bounds of a node bubble
	const pos = nodePositions[nodeId];
	if (!pos) return null;
	
	// Use stored actual rendered dimensions if available (for arrow calculations)
	let width = pos.boxWidth;
	let height = pos.boxHeight;
	
	// Fall back to estimates if not yet rendered
	if (!width || !height) {
		const node = nodes.find(n => n.id === nodeId);
		if (!node) return null;
		
		const lowLevel = node.lowLevel || [];
		const padding = 15;
		const titleHeight = 20;
		const lineHeight = 16;
		const bulletSpacing = 4;
		const maxTextWidth = 200;
		
		// Calculate width using glossary titles
		const titleText = getGlossaryTitle(node.label);
		let maxWidth = Math.max(measureTextWidth(titleText, '14px', 'bold'), maxTextWidth);
		if (lowLevel.length > 0) {
			const maxItemWidth = Math.max(...lowLevel.map(item => {
				const parsed = parseLowLevelItem(item);
				return measureTextWidth(parsed.display, '11px');
			}));
			maxWidth = Math.max(maxWidth, maxItemWidth + 30);
		}
		width = Math.min(maxWidth, 250);
		
		// Calculate height
		const bulletHeight = lowLevel.length > 0 ? lowLevel.length * (lineHeight + bulletSpacing) : 0;
		height = titleHeight + bulletHeight + (padding * 2);
	}
	
	// Calculate actual box center from text starting position
	const boxCenterX = pos.x; // X is same (centered)
	const boxCenterY = pos.y + (pos.boxOffsetY || 0); // Y offset by stored amount
	
	return {
		x: boxCenterX - width / 2,
		y: boxCenterY - height / 2,
		width: width,
		height: height,
		centerX: boxCenterX,
		centerY: boxCenterY
	};
}

function getConnectionLineEndpoint(fromPos, toPos, fromBounds, toBounds) {
	// Calculate where line should start/end to avoid overlapping bubbles
	// Returns {x1, y1, x2, y2} for the connection line
	
	const dx = toPos.x - fromPos.x;
	const dy = toPos.y - fromPos.y;
	const dist = Math.sqrt(dx * dx + dy * dy);
	if (dist === 0) return {x1: fromPos.x, y1: fromPos.y, x2: toPos.x, y2: toPos.y};
	
	// Unit vector
	const ux = dx / dist;
	const uy = dy / dist;
	
	// Padding distance for arrow clearance
	const padding = 12;
	
	// Calculate distance from center to edge along the line direction for fromBounds
	// If fromBounds is null, we're coming from a connection box center, so start from center (offset = 0)
	let fromOffset = 0;
	if (fromBounds) {
		// Create padded box (extend padding pixels outward on all sides)
		const paddedBox = {
			x: fromBounds.x - padding,
			y: fromBounds.y - padding,
			width: fromBounds.width + (padding * 2),
			height: fromBounds.height + (padding * 2)
		};
		
		// Calculate intersections with each edge of the padded box
		const intersections = [];
		
		// Left edge: x = paddedBox.x
		if (ux !== 0) {
			const t = (paddedBox.x - fromPos.x) / ux;
			if (t > 0) {
				const y = fromPos.y + t * uy;
				if (y >= paddedBox.y && y <= paddedBox.y + paddedBox.height) {
					intersections.push(t);
				}
			}
		}
		
		// Right edge: x = paddedBox.x + paddedBox.width
		if (ux !== 0) {
			const t = (paddedBox.x + paddedBox.width - fromPos.x) / ux;
			if (t > 0) {
				const y = fromPos.y + t * uy;
				if (y >= paddedBox.y && y <= paddedBox.y + paddedBox.height) {
					intersections.push(t);
				}
			}
		}
		
		// Top edge: y = paddedBox.y
		if (uy !== 0) {
			const t = (paddedBox.y - fromPos.y) / uy;
			if (t > 0) {
				const x = fromPos.x + t * ux;
				if (x >= paddedBox.x && x <= paddedBox.x + paddedBox.width) {
					intersections.push(t);
				}
			}
		}
		
		// Bottom edge: y = paddedBox.y + paddedBox.height
		if (uy !== 0) {
			const t = (paddedBox.y + paddedBox.height - fromPos.y) / uy;
			if (t > 0) {
				const x = fromPos.x + t * ux;
				if (x >= paddedBox.x && x <= paddedBox.x + paddedBox.width) {
					intersections.push(t);
				}
			}
		}
		
		if (intersections.length > 0) {
			const minT = Math.min(...intersections);
			fromOffset = minT;
		}
	}
	
	// Calculate distance from center to edge along the line direction for toBounds
	// If toBounds is null, we're going to a connection box center, so go all the way (offset = 0)
	let toOffset = 0;
	if (toBounds) {
		// Create padded box (extend padding pixels outward on all sides)
		const paddedBox = {
			x: toBounds.x - padding,
			y: toBounds.y - padding,
			width: toBounds.width + (padding * 2),
			height: toBounds.height + (padding * 2)
		};
		
		const intersections = [];
		
		// Left edge
		if (ux !== 0) {
			const t = (paddedBox.x - toPos.x) / -ux;
			if (t > 0) {
				const y = toPos.y + t * (-uy);
				if (y >= paddedBox.y && y <= paddedBox.y + paddedBox.height) {
					intersections.push(t);
				}
			}
		}
		
		// Right edge
		if (ux !== 0) {
			const t = (paddedBox.x + paddedBox.width - toPos.x) / -ux;
			if (t > 0) {
				const y = toPos.y + t * (-uy);
				if (y >= paddedBox.y && y <= paddedBox.y + paddedBox.height) {
					intersections.push(t);
				}
			}
		}
		
		// Top edge
		if (uy !== 0) {
			const t = (paddedBox.y - toPos.y) / -uy;
			if (t > 0) {
				const x = toPos.x + t * (-ux);
				if (x >= paddedBox.x && x <= paddedBox.x + paddedBox.width) {
					intersections.push(t);
				}
			}
		}
		
		// Bottom edge
		if (uy !== 0) {
			const t = (paddedBox.y + paddedBox.height - toPos.y) / -uy;
			if (t > 0) {
				const x = toPos.x + t * (-ux);
				if (x >= paddedBox.x && x <= paddedBox.x + paddedBox.width) {
					intersections.push(t);
				}
			}
		}
		
		if (intersections.length > 0) {
			const minT = Math.min(...intersections);
			toOffset = minT;
		}
	}
	
	// Calculate endpoints
	const x1 = fromPos.x + ux * fromOffset;
	const y1 = fromPos.y + uy * fromOffset;
	const x2 = toPos.x - ux * toOffset;
	const y2 = toPos.y - uy * toOffset;
	
	return {x1, y1, x2, y2};
}

function render() {
	if (!canvas) return;
	canvas.innerHTML = '';
	
	// Create transform group for panning
	svgGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
	svgGroup.setAttribute('id', 'pan-group');
	applyPanTransform();
	
	// Draw grid if enabled (behind everything) - editor mode only
	if (typeof gridEnabled !== 'undefined' && gridEnabled && typeof drawGrid === 'function') {
		drawGrid();
	}
	
	// Create arrow markers first
	const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
	
	// Forward arrow
	const forwardMarker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
	forwardMarker.setAttribute('id', 'arrow-forward');
	forwardMarker.setAttribute('markerWidth', '10');
	forwardMarker.setAttribute('markerHeight', '10');
	forwardMarker.setAttribute('refX', '8');
	forwardMarker.setAttribute('refY', '5');
	forwardMarker.setAttribute('orient', 'auto');
	forwardMarker.setAttribute('markerUnits', 'userSpaceOnUse');
	const forwardPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
	forwardPath.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
	forwardPath.setAttribute('fill', '#999');
	forwardMarker.appendChild(forwardPath);
	defs.appendChild(forwardMarker);
	
	// Bidirectional arrow (for end)
	const biEndMarker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
	biEndMarker.setAttribute('id', 'arrow-bidirectional');
	biEndMarker.setAttribute('markerWidth', '10');
	biEndMarker.setAttribute('markerHeight', '10');
	biEndMarker.setAttribute('refX', '8');
	biEndMarker.setAttribute('refY', '5');
	biEndMarker.setAttribute('orient', 'auto');
	biEndMarker.setAttribute('markerUnits', 'userSpaceOnUse');
	const biEndPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
	biEndPath.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
	biEndPath.setAttribute('fill', '#999');
	biEndMarker.appendChild(biEndPath);
	defs.appendChild(biEndMarker);
	
	// Bidirectional arrow (for start - reversed)
	const biStartMarker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
	biStartMarker.setAttribute('id', 'arrow-bidirectional-start');
	biStartMarker.setAttribute('markerWidth', '10');
	biStartMarker.setAttribute('markerHeight', '10');
	biStartMarker.setAttribute('refX', '10');
	biStartMarker.setAttribute('refY', '5');
	biStartMarker.setAttribute('orient', 'auto');
	biStartMarker.setAttribute('markerUnits', 'userSpaceOnUse');
	const biStartPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
	biStartPath.setAttribute('d', 'M 10 0 L 0 5 L 10 10 z');
	biStartPath.setAttribute('fill', '#999');
	biStartMarker.appendChild(biStartPath);
	defs.appendChild(biStartMarker);
	svgGroup.appendChild(defs);
	
	// Function to render arrows (can be called multiple times)
	function renderArrows() {
		// Remove existing arrows
		const existingArrows = svgGroup.querySelectorAll('line[stroke="#999"]');
		existingArrows.forEach(el => el.remove());
		
		// Calculate node bounds for all nodes (use actual dimensions if available)
		const nodeBoundsMap = {};
		nodes.forEach(node => {
			const bounds = getNodeBounds(node.id);
			if (bounds) {
				nodeBoundsMap[node.id] = bounds;
			}
		});
		
		// Find insertion point (after defs, before boxes/text)
		const defsElement = svgGroup.querySelector('defs');
		
		// Render connection lines (so they appear behind text boxes)
		const arrowLines = [];
		connections.forEach(conn => {
		const fromPos = nodePositions[conn.from];
		const toPos = nodePositions[conn.to];
		if (!fromPos || !toPos) return;
		
		// Generate unique connection ID
		const connId = `${conn.from}->${conn.to}`;
		
		// Get or initialize connection box position
		const savedPos = connectionPositions[connId];
		if (!savedPos) {
			// Initialize at midpoint between nodes
			connectionPositions[connId] = {
				x: (fromPos.x + toPos.x) / 2,
				y: (fromPos.y + toPos.y) / 2
			};
		}
		const textStartPos = connectionPositions[connId] || {};
		// Calculate box center from text starting position (for arrows)
		const connBoxPos = {
			x: textStartPos.x || ((fromPos.x + toPos.x) / 2),
			y: (textStartPos.y || ((fromPos.y + toPos.y) / 2)) + (textStartPos.boxOffsetY || 0)
		};
		
		// Get node bounds for proper line endpoint calculation
		const fromBounds = nodeBoundsMap[conn.from];
		const toBounds = nodeBoundsMap[conn.to];
		
		// Calculate line endpoints from node edges
		// Line 1: from connection box (blue) to source node (green)
		const fromEndpoints = getConnectionLineEndpoint(connBoxPos, fromPos, null, fromBounds);
		// Line 2: from connection box (blue) to target node (green)
		const toEndpoints = getConnectionLineEndpoint(connBoxPos, toPos, null, toBounds);
		
		// Line 1: from connection box center (blue) to source node edge (green)
		const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
		line1.setAttribute('x1', connBoxPos.x);
		line1.setAttribute('y1', connBoxPos.y);
		line1.setAttribute('x2', fromEndpoints.x2);
		line1.setAttribute('y2', fromEndpoints.y2);
		line1.setAttribute('stroke', '#999');
		line1.setAttribute('stroke-width', '2');
		
		// Line 2: from connection box center (blue) to target node edge (green)
		const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
		line2.setAttribute('x1', connBoxPos.x);
		line2.setAttribute('y1', connBoxPos.y);
		line2.setAttribute('x2', toEndpoints.x2);
		line2.setAttribute('y2', toEndpoints.y2);
		line2.setAttribute('stroke', '#999');
		line2.setAttribute('stroke-width', '2');
		
		// Add arrowheads based on connection type (all arrowheads use marker-end only)
		if (conn.type === 'forward') {
			// Forward: arrow on line2 going to target node
			line2.setAttribute('marker-end', 'url(#arrow-forward)');
		} else if (conn.type === 'bidirectional') {
			// Bidirectional: arrows on both lines at their ends (pointing to green boxes)
			line1.setAttribute('marker-end', 'url(#arrow-bidirectional)');
			line2.setAttribute('marker-end', 'url(#arrow-bidirectional)');
		}
		// undirected has no arrows
		
		// Collect arrow lines to insert
		arrowLines.push(line1, line2);
		});
		
		// Insert all arrows right after defs (behind boxes/text)
		if (defsElement) {
			arrowLines.forEach(line => {
				svgGroup.insertBefore(line, defsElement.nextSibling);
			});
		} else {
			// Fallback if defs not found (shouldn't happen)
			arrowLines.forEach(line => svgGroup.appendChild(line));
		}
	}
	
	// Render arrows initially (for dragging responsiveness, may use estimates)
	renderArrows();
	
	// Setup callback array for round-robin text rendering
	const textCallbacks = [];
	
	// Create callbacks for connections
	connections.forEach(conn => {
		const fromPos = nodePositions[conn.from];
		const toPos = nodePositions[conn.to];
		if (!fromPos || !toPos) return;
		
		const connId = `${conn.from}->${conn.to}`;
		const connBoxPos = connectionPositions[connId] || {};
		const startX = connBoxPos.x || ((fromPos.x + toPos.x) / 2);
		const startY = connBoxPos.y || ((fromPos.y + toPos.y) / 2);
		const connLowLevel = conn.lowLevel || [];
		
		const connPadding = 8;
		const connBulletSpacing = 2;
		const connMinWidth = 80;
		const connMaxTextWidth = 200;
		
		// Build lines array
		const lines = [];
		if (conn.description) {
			lines.push({ type: 'title', text: getGlossaryTitle(conn.description), term: conn.description });
		}
		connLowLevel.forEach(item => {
			const parsed = parseLowLevelItem(item);
			let fullText = '';
			if (parsed.hasDisplayText && parsed.termTitle) {
				fullText = parsed.termTitle;
				if (parsed.display && parsed.display.trim() !== '') {
					fullText += ': ' + parsed.display;
				}
			} else {
				fullText = parsed.display;
			}
			lines.push({ type: 'bullet', text: fullText, term: parsed.term, hasGlossary: parsed.hasGlossary });
		});
		
		// Create callback object
		const callback = {
			type: 'connection',
			connId: connId,
			startX: startX,
			startY: startY,
			lines: lines,
			lineIndex: 0,
			currentY: startY,
			textElements: [],
			maxWidth: 0,
			lastDrawnElement: null,
			lastLineHeight: 0, // Track height of last rendered line
			bulletGroup: null, // Group for bullet list (centered, left-aligned text inside)
			bulletGroupY: null, // Y position where bullet group starts
			connPadding: connPadding,
			connBulletSpacing: connBulletSpacing,
			connMinWidth: connMinWidth,
			connMaxTextWidth: connMaxTextWidth,
			heartbeat: function() {
				// Try to measure last drawn element
				if (this.lastDrawnElement) {
					const bbox = this.lastDrawnElement.getBBox();
					// Check if measurement is valid (has real numbers)
					if (bbox.width > 0 || bbox.height > 0) {
						// Valid measurement - update state
						const lineType = this.lines[this.lineIndex].type;
						if (lineType === 'title') {
							this.maxWidth = Math.max(this.maxWidth, bbox.width);
						} else {
							this.maxWidth = Math.max(this.maxWidth, bbox.width + 30); // +30 for bullet + padding
						}
						this.lastLineHeight = bbox.height; // Track this line's height
						this.currentY += bbox.height + this.connBulletSpacing;
						this.lastDrawnElement = null; // Clear so we can draw next line
						this.lineIndex++;
					} else {
						// Measurement not ready yet - pass, stay in callback array
						return 'wait';
					}
				}
				
				// Check if done
				if (this.lineIndex >= this.lines.length) {
					// Store final bounds before returning (subtract last line height, keep spacing for proper padding)
					this.boxBottomY = this.currentY - this.lastLineHeight;
					return 'done';
				}
				
				// Draw next line
				const line = this.lines[this.lineIndex];
				const estimatedLeftX = this.startX - (this.connMaxTextWidth / 2) + this.connPadding;
				
				if (line.type === 'title') {
					const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
					title.setAttribute('class', 'connection-title');
					title.setAttribute('x', this.startX);
					title.setAttribute('y', this.currentY);
					title.setAttribute('text-anchor', 'middle');
					title.textContent = line.text;
					
					if (getGlossaryDescription(line.term)) {
						title.setAttribute('data-glossary-term', line.term);
						title.style.cursor = 'pointer';
						title.style.pointerEvents = 'all';
						title.addEventListener('mousedown', (e) => {
							e.stopPropagation();
							e.preventDefault();
							isClickingGlossaryLink = true;
						});
						title.addEventListener('click', (e) => {
							e.stopPropagation();
							e.preventDefault();
							showGlossaryModal(line.term);
							isClickingGlossaryLink = false;
						});
					}
					
					svgGroup.appendChild(title);
					this.textElements.push(title);
					this.lastDrawnElement = title;
				} else if (line.type === 'bullet') {
					// Create bullet group on first bullet
					if (!this.bulletGroup) {
						this.bulletGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
						this.bulletGroupY = this.currentY;
						svgGroup.appendChild(this.bulletGroup);
					}
					
					// Calculate Y relative to bullet group start
					const relativeY = this.currentY - this.bulletGroupY;
					
					// Draw bullet left-aligned within group (starting from left edge)
					const bulletX = this.connPadding;
					const bullet = document.createElementNS('http://www.w3.org/2000/svg', 'text');
					bullet.setAttribute('class', 'connection-bullet');
					bullet.setAttribute('x', bulletX);
					bullet.setAttribute('y', relativeY);
					bullet.textContent = '•';
					this.bulletGroup.appendChild(bullet);
					this.textElements.push(bullet);
					
					const bulletText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
					bulletText.setAttribute('class', 'connection-bullet');
					bulletText.setAttribute('x', bulletX + 10);
					bulletText.setAttribute('y', relativeY);
					bulletText.textContent = line.text;
					
					if (line.hasGlossary && line.term) {
						bulletText.setAttribute('data-glossary-term', line.term);
						bulletText.style.cursor = 'pointer';
						bulletText.style.fill = '#ffffff';
						bulletText.style.pointerEvents = 'all';
						bulletText.addEventListener('mousedown', (e) => {
							e.stopPropagation();
							e.preventDefault();
							isClickingGlossaryLink = true;
						});
						bulletText.addEventListener('click', (e) => {
							e.stopPropagation();
							e.preventDefault();
							showGlossaryModal(line.term);
							isClickingGlossaryLink = false;
						});
					} else {
						bulletText.style.fill = '#ffffff';
					}
					
					this.bulletGroup.appendChild(bulletText);
					this.textElements.push(bulletText);
					this.lastDrawnElement = bulletText; // Measure the text, not the bullet
				}
				
				return 'drew';
			}
		};
		
		textCallbacks.push(callback);
	});
	
	// Create callbacks for nodes
	nodes.forEach(node => {
		const pos = nodePositions[node.id] || {};
		const startX = pos.x || 100;
		const startY = pos.y || 100;
		const lowLevel = node.lowLevel || [];
		
		const padding = 15;
		const bulletSpacing = 4;
		const maxTextWidth = 250;
		
		// Build lines array
		const lines = [];
		lines.push({ type: 'title', text: getGlossaryTitle(node.label), term: node.label });
		lowLevel.forEach(item => {
			const parsed = parseLowLevelItem(item);
			let fullText = '';
			if (parsed.hasDisplayText && parsed.termTitle) {
				fullText = parsed.termTitle;
				if (parsed.display && parsed.display.trim() !== '') {
					fullText += ': ' + parsed.display;
				}
			} else {
				fullText = parsed.display;
			}
			lines.push({ type: 'bullet', text: fullText, term: parsed.term, hasGlossary: parsed.hasGlossary });
		});
		
		// Create node group
		const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
		group.setAttribute('class', 'node');
		if (typeof startDrag === 'function') {
			group.style.cursor = 'grab';
		}
		
		// Create callback object
		const callback = {
			type: 'node',
			nodeId: node.id,
			group: group,
			startX: startX,
			startY: startY,
			lines: lines,
			lineIndex: 0,
			currentY: startY,
			textElements: [],
			maxWidth: 0,
			lastDrawnElement: null,
			lastLineHeight: 0, // Track height of last rendered line
			bulletGroup: null, // Group for bullet list (centered, left-aligned text inside)
			bulletGroupY: null, // Y position where bullet group starts
			padding: padding,
			bulletSpacing: bulletSpacing,
			maxTextWidth: maxTextWidth,
			heartbeat: function() {
				// Try to measure last drawn element
				if (this.lastDrawnElement) {
					const bbox = this.lastDrawnElement.getBBox();
					// Check if measurement is valid (has real numbers)
					if (bbox.width > 0 || bbox.height > 0) {
						// Valid measurement - update state
						const lineType = this.lines[this.lineIndex].type;
						if (lineType === 'title') {
							this.maxWidth = Math.max(this.maxWidth, bbox.width);
						} else {
							this.maxWidth = Math.max(this.maxWidth, bbox.width + 30); // +30 for bullet + padding
						}
						this.lastLineHeight = bbox.height; // Track this line's height
						this.currentY += bbox.height + this.bulletSpacing;
						this.lastDrawnElement = null; // Clear so we can draw next line
						this.lineIndex++;
					} else {
						// Measurement not ready yet - pass, stay in callback array
						return 'wait';
					}
				}
				
				// Check if done
				if (this.lineIndex >= this.lines.length) {
					// Store final bounds before returning (subtract last line height, keep spacing for proper padding)
					this.boxBottomY = this.currentY - this.lastLineHeight;
					return 'done';
				}
				
				// Draw next line
				const line = this.lines[this.lineIndex];
				const estimatedLeftX = this.startX - (this.maxTextWidth / 2) + this.padding;
				
				if (line.type === 'title') {
					const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
					title.setAttribute('class', 'node-title');
					title.setAttribute('x', this.startX);
					title.setAttribute('y', this.currentY);
					title.setAttribute('text-anchor', 'middle');
					title.textContent = line.text;
					
					if (getGlossaryDescription(line.term)) {
						title.setAttribute('data-glossary-term', line.term);
						title.style.cursor = 'pointer';
						title.style.pointerEvents = 'all';
						title.addEventListener('mousedown', (e) => {
							e.stopPropagation();
							e.preventDefault();
							isClickingGlossaryLink = true;
						});
						title.addEventListener('click', (e) => {
							e.stopPropagation();
							e.preventDefault();
							showGlossaryModal(line.term);
							isClickingGlossaryLink = false;
						});
					} else {
						// Title is not a glossary link
						// In editor mode, add drag handler; in deploy mode, add pan handler
						if (typeof startDrag === 'function') {
							title.addEventListener('mousedown', (e) => {
								if (!glossaryModalOpen && !isClickingGlossaryLink) {
									startDrag(this.nodeId, e);
								}
							});
						} else {
							title.addEventListener('mousedown', (e) => {
								if (!glossaryModalOpen && !isClickingGlossaryLink) {
									startPan(e);
								}
							});
						}
					}
					
					this.group.appendChild(title);
					this.textElements.push(title);
					this.lastDrawnElement = title;
				} else if (line.type === 'bullet') {
					// Create bullet group on first bullet
					if (!this.bulletGroup) {
						this.bulletGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
						this.bulletGroupY = this.currentY;
						this.group.appendChild(this.bulletGroup);
					}
					
					// Calculate Y relative to bullet group start
					const relativeY = this.currentY - this.bulletGroupY;
					
					// Draw bullet left-aligned within group (starting from left edge)
					const bulletX = this.padding;
					const bullet = document.createElementNS('http://www.w3.org/2000/svg', 'text');
					bullet.setAttribute('class', 'node-bullet');
					bullet.setAttribute('x', bulletX);
					bullet.setAttribute('y', relativeY);
					bullet.textContent = '•';
					this.bulletGroup.appendChild(bullet);
					this.textElements.push(bullet);
					
					const bulletText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
					bulletText.setAttribute('class', 'node-bullet');
					bulletText.setAttribute('x', bulletX + 12);
					bulletText.setAttribute('y', relativeY);
					bulletText.textContent = line.text;
					
					if (line.hasGlossary && line.term) {
						bulletText.setAttribute('data-glossary-term', line.term);
						bulletText.style.cursor = 'pointer';
						bulletText.style.fill = '#ffffff';
						bulletText.style.pointerEvents = 'all';
						bulletText.addEventListener('mousedown', (e) => {
							e.stopPropagation();
							e.preventDefault();
							isClickingGlossaryLink = true;
						});
						bulletText.addEventListener('click', (e) => {
							e.stopPropagation();
							e.preventDefault();
							showGlossaryModal(line.term);
							isClickingGlossaryLink = false;
						});
					} else {
						bulletText.style.fill = '#ffffff';
					}
					
					this.bulletGroup.appendChild(bulletText);
					this.textElements.push(bulletText);
					this.lastDrawnElement = bulletText; // Measure the text, not the bullet
				}
				
				return 'drew';
			}
		};
		
		textCallbacks.push(callback);
	});
	
	// Store finished callbacks so we can draw boxes
	const finishedCallbacks = [];
	
	// Round-robin loop to render text line by line
	function processTextCallbacks() {
		if (textCallbacks.length === 0) {
			// All done - draw boxes
			drawTextBoxes();
			return;
		}
		
		// Call heartbeat on all callbacks and collect finished ones
		const stillActive = [];
		textCallbacks.forEach(cb => {
			// Ensure node groups are in DOM before rendering (standardize with connections)
			if (cb.type === 'node' && cb.group && !cb.group.parentNode) {
				svgGroup.appendChild(cb.group);
			}
			
			const result = cb.heartbeat();
			if (result === 'done') {
				finishedCallbacks.push(cb);
			} else {
				stillActive.push(cb);
			}
		});
		
		textCallbacks.length = 0;
		textCallbacks.push(...stillActive);
		
		// Delay and continue
		setTimeout(processTextCallbacks, 20);
	}
	
	// Function to draw boxes after all text is rendered
	function drawTextBoxes() {
		finishedCallbacks.forEach(cb => {
			if (cb.type === 'connection') {
				// Center bullet group if it exists
				if (cb.bulletGroup) {
					const groupBbox = cb.bulletGroup.getBBox();
					const groupCenterX = groupBbox.x + (groupBbox.width / 2);
					const offsetX = cb.startX - groupCenterX;
					// Position group: translate X to center it, Y to bulletGroupY
					cb.bulletGroup.setAttribute('transform', `translate(${offsetX} ${cb.bulletGroupY})`);
				}
				
				// Get bounds: measure title for top, use stored bottom Y
				let minY, maxY;
				
				// Measure title to get top Y
				const title = cb.textElements.find(el => el.getAttribute('class') === 'connection-title');
				if (title) {
					const titleBbox = title.getBBox();
					minY = titleBbox.y;
				} else {
					// No title, use startY
					minY = cb.startY;
				}
				
				// Use stored bottom Y (calculated during rendering)
				maxY = cb.boxBottomY;
				
				const connWidth = Math.max(Math.min(cb.maxWidth + (cb.connPadding * 2), cb.connMaxTextWidth), cb.connMinWidth);
				const connHeight = (maxY - minY) + (cb.connPadding * 2);
				const connX = cb.startX - (connWidth / 2);
				const connY = minY - cb.connPadding;
				
				const connRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
				connRect.setAttribute('x', connX);
				connRect.setAttribute('y', connY);
				connRect.setAttribute('width', connWidth);
				connRect.setAttribute('height', connHeight);
				connRect.setAttribute('rx', '6');
				connRect.setAttribute('fill', '#1a3a6b');
				connRect.setAttribute('stroke', '#79c0ff');
				connRect.setAttribute('stroke-width', '2');
				
				// In editor mode, add drag handlers
				if (typeof startConnectionDrag === 'function') {
					connRect.style.cursor = 'grab';
					connRect.addEventListener('mousedown', (e) => {
						const target = e.target;
						if (target && target.nodeName === 'text' && target.hasAttribute && target.hasAttribute('data-glossary-term')) {
							e.stopPropagation();
							return;
						}
						if (isClickingGlossaryLink || glossaryModalOpen) {
							e.stopPropagation();
							return;
						}
						startConnectionDrag(cb.connId, e);
					});
					connRect.addEventListener('touchstart', (e) => {
						if (e.touches.length === 1 && !glossaryModalOpen && !isClickingGlossaryLink) {
							const touch = e.touches[0];
							startConnectionDrag(cb.connId, { clientX: touch.clientX, clientY: touch.clientY });
							e.stopPropagation();
						}
					}, { passive: false });
				}
				
				if (cb.textElements.length > 0) {
					svgGroup.insertBefore(connRect, cb.textElements[0]);
				} else {
					svgGroup.appendChild(connRect);
				}
				
				const actualBoxCenterX = connX + (connWidth / 2);
				const actualBoxCenterY = connY + (connHeight / 2);
				
				// Calculate vertical offset from text start to box center
				const boxOffsetY = actualBoxCenterY - cb.startY;
				
				// Save text starting position (not box center) for stable reference
				// Also save actual rendered dimensions for arrow calculations
				connectionPositions[cb.connId] = {
					x: cb.startX,
					y: cb.startY,
					boxOffsetY: boxOffsetY,
					boxWidth: connWidth,
					boxHeight: connHeight
				};
			} else if (cb.type === 'node') {
				// Center bullet group if it exists
				if (cb.bulletGroup) {
					const groupBbox = cb.bulletGroup.getBBox();
					const groupCenterX = groupBbox.x + (groupBbox.width / 2);
					const offsetX = cb.startX - groupCenterX;
					// Position group: translate X to center it, Y to bulletGroupY
					cb.bulletGroup.setAttribute('transform', `translate(${offsetX} ${cb.bulletGroupY})`);
				}
				
				// Get bounds: measure title for top, use stored bottom Y
				let minY, maxY;
				
				// Measure title to get top Y
				const title = cb.textElements.find(el => el.getAttribute('class') === 'node-title');
				if (title) {
					const titleBbox = title.getBBox();
					minY = titleBbox.y;
				} else {
					// No title, use startY
					minY = cb.startY;
				}
				
				// Use stored bottom Y (calculated during rendering)
				maxY = cb.boxBottomY;
				
				const width = Math.min(Math.max(cb.maxWidth + (cb.padding * 2), 0), cb.maxTextWidth);
				const height = (maxY - minY) + (cb.padding * 2);
				const x = cb.startX - (width / 2);
				const y = minY - cb.padding;
				
				const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
				rect.setAttribute('x', x);
				rect.setAttribute('y', y);
				rect.setAttribute('width', width);
				rect.setAttribute('height', height);
				rect.setAttribute('rx', '8');
				rect.setAttribute('fill', '#1a4d2a');
				rect.setAttribute('stroke', '#56d364');
				rect.setAttribute('stroke-width', '3');
				
				// In editor mode, add drag handlers
				if (typeof startDrag === 'function') {
					rect.style.cursor = 'grab';
					rect.addEventListener('mousedown', (e) => {
						const target = e.target;
						if (target && target.nodeName === 'text' && target.hasAttribute && target.hasAttribute('data-glossary-term')) {
							e.stopPropagation();
							return;
						}
						if (isClickingGlossaryLink || glossaryModalOpen) {
							e.stopPropagation();
							return;
						}
						startDrag(cb.nodeId, e);
					});
					rect.addEventListener('touchstart', (e) => {
						if (e.touches.length === 1 && !glossaryModalOpen && !isClickingGlossaryLink) {
							const touch = e.touches[0];
							startDrag(cb.nodeId, { clientX: touch.clientX, clientY: touch.clientY });
							e.stopPropagation();
						}
					}, { passive: false });
				}
				
				if (cb.textElements.length > 0) {
					cb.group.insertBefore(rect, cb.textElements[0]);
				} else {
					cb.group.appendChild(rect);
				}
				
				const actualBoxCenterX = x + (width / 2);
				const actualBoxCenterY = y + (height / 2);
				
				// Calculate vertical offset from text start to box center
				const boxOffsetY = actualBoxCenterY - cb.startY;
				
				// Save text starting position (not box center) for stable reference
				// Also save actual rendered dimensions for arrow calculations
				nodePositions[cb.nodeId] = {
					x: cb.startX,
					y: cb.startY,
					boxOffsetY: boxOffsetY,
					boxWidth: width,
					boxHeight: height
				};
			}
		});
		
		// Redraw arrows with actual box dimensions
		renderArrows();
	}
	
	// Append the transform group to canvas before rendering (needed for measurements)
	canvas.appendChild(svgGroup);
	
	// Start the rendering process
	processTextCallbacks();
}


