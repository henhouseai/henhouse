// Layout management functions

function switchInfographic() {
	const selector = document.getElementById('infographicSelector');
	const selectedId = selector.value;
	
	if (!selectedId) {
		nodes = [];
		connections = [];
		nodePositions = {};
		render();
		return;
	}
	
	// Save current positions before switching - but only if we actually have positions to save
	if (currentInfographicId) {
		if (!allPositions[currentInfographicId]) {
			allPositions[currentInfographicId] = {};
		}
		if (nodePositions && Object.keys(nodePositions).length > 0) {
			allPositions[currentInfographicId].nodes = JSON.parse(JSON.stringify(nodePositions));
		}
		if (connectionPositions && Object.keys(connectionPositions).length > 0) {
			allPositions[currentInfographicId].connections = JSON.parse(JSON.stringify(connectionPositions));
		}
	}
	
	// Find and load selected infographic
	const infographic = allInfographics.find(inf => inf.id === selectedId);
	if (!infographic) return;
	
	currentInfographicId = selectedId;
	nodes = infographic.nodes || [];
	connections = infographic.connections || [];
	
	// Reset pan offset and zoom when switching infographics
	panOffset = { x: 0, y: 0 };
	zoomLevel = 1.0;
	isPanning = false;
	applyPanTransform();
	
	// Restore saved positions for this infographic, or initialize new ones
	if (allPositions[currentInfographicId] && Object.keys(allPositions[currentInfographicId]).length > 0) {
		// Deep copy positions to ensure we get the actual values
		const saved = allPositions[currentInfographicId];
		nodePositions = saved.nodes ? JSON.parse(JSON.stringify(saved.nodes)) : {};
		connectionPositions = saved.connections ? JSON.parse(JSON.stringify(saved.connections)) : {};
	} else {
		nodePositions = {};
		connectionPositions = {};
	}
	
	// Initialize positions if not saved
	nodes.forEach((node, i) => {
		if (!nodePositions[node.id]) {
			const angle = (i / nodes.length) * Math.PI * 2;
			const radius = 250;
			const centerX = canvas.clientWidth / 2;
			const centerY = canvas.clientHeight / 2;
			nodePositions[node.id] = {
				x: centerX + Math.cos(angle) * radius,
				y: centerY + Math.sin(angle) * radius
			};
		}
	});
	
	// Initialize connection box positions if not saved
	connections.forEach(conn => {
		const connId = `${conn.from}->${conn.to}`;
		const fromPos = nodePositions[conn.from];
		const toPos = nodePositions[conn.to];
		if (!connectionPositions[connId] && fromPos && toPos) {
			connectionPositions[connId] = {
				x: (fromPos.x + toPos.x) / 2,
				y: (fromPos.y + toPos.y) / 2
			};
		}
	});
	
	render();
	
	// Editor mode: Build glossary lists after switching
	if (typeof buildHighLevelGlossaryList === 'function') {
		buildHighLevelGlossaryList();
		buildConceptsList();
		buildDetailsList();
		buildConnectionsList();
		buildConnectionDetailsList();
		buildGlossaryList();
	}
	
	// Auto zoom to fit after rendering
	setTimeout(() => {
		zoomToFit();
		// Fade out startup overlay after zoom completes
		setTimeout(() => {
			fadeOutStartupOverlay();
		}, 200);
	}, 100);
}

function resetLayout() {
	nodes.forEach((node, i) => {
		const angle = (i / nodes.length) * Math.PI * 2;
		const radius = Math.min(canvas.clientWidth, canvas.clientHeight) * 0.3;
		const centerX = canvas.clientWidth / 2;
		const centerY = canvas.clientHeight / 2;
		nodePositions[node.id] = {
			x: centerX + Math.cos(angle) * radius,
			y: centerY + Math.sin(angle) * radius
		};
	});
	// Reset connection positions to midpoints
	connections.forEach(conn => {
		const connId = `${conn.from}->${conn.to}`;
		const fromPos = nodePositions[conn.from];
		const toPos = nodePositions[conn.to];
		if (fromPos && toPos) {
			connectionPositions[connId] = {
				x: (fromPos.x + toPos.x) / 2,
				y: (fromPos.y + toPos.y) / 2
			};
		}
	});
	// Save positions after reset
	if (currentInfographicId) {
		if (!allPositions[currentInfographicId]) {
			allPositions[currentInfographicId] = {};
		}
		allPositions[currentInfographicId].nodes = { ...nodePositions };
		allPositions[currentInfographicId].connections = { ...connectionPositions };
	}
	render();
}

function centerLayout() {
	const centerX = canvas.clientWidth / 2;
	const centerY = canvas.clientHeight / 2;
	nodes.forEach((node, i) => {
		const angle = (i / nodes.length) * Math.PI * 2;
		const radius = 150;
		nodePositions[node.id] = {
			x: centerX + Math.cos(angle) * radius,
			y: centerY + Math.sin(angle) * radius
		};
	});
	// Reset connection positions to midpoints
	connections.forEach(conn => {
		const connId = `${conn.from}->${conn.to}`;
		const fromPos = nodePositions[conn.from];
		const toPos = nodePositions[conn.to];
		if (fromPos && toPos) {
			connectionPositions[connId] = {
				x: (fromPos.x + toPos.x) / 2,
				y: (fromPos.y + toPos.y) / 2
			};
		}
	});
	// Save positions after center
	if (currentInfographicId) {
		if (!allPositions[currentInfographicId]) {
			allPositions[currentInfographicId] = {};
		}
		allPositions[currentInfographicId].nodes = { ...nodePositions };
		allPositions[currentInfographicId].connections = { ...connectionPositions };
	}
	render();
}

function exportLayout() {
	// Check if we have an active infographic
	if (!currentInfographicId) {
		alert('Please select an infographic first');
		return;
	}
	
	// Save current positions before exporting
	if (currentInfographicId) {
		if (!allPositions[currentInfographicId]) {
			allPositions[currentInfographicId] = {};
		}
		allPositions[currentInfographicId].nodes = JSON.parse(JSON.stringify(nodePositions));
		allPositions[currentInfographicId].connections = JSON.parse(JSON.stringify(connectionPositions));
	}
	
	// Find the current infographic
	const currentInfographic = allInfographics.find(inf => inf.id === currentInfographicId);
	if (!currentInfographic) {
		alert('Current infographic not found');
		return;
	}
	
	// Export only the current infographic with only its positions
	// Export format: flat object with both node and connection positions (connection IDs have "->" so won't conflict)
	const currentPositions = allPositions[currentInfographicId] || {};
	const exportedPositions = {
		...(currentPositions.nodes || {}),
		...(currentPositions.connections || {})
	};
	const config = {
		infographics: [{
			id: currentInfographic.id,
			title: currentInfographic.title,
			nodes: currentInfographic.nodes,
			connections: currentInfographic.connections
		}],
		positions: {
			[currentInfographicId]: exportedPositions
		}
	};
	
	// Determine variable name based on infographic id
	// Convert kebab-case ID to camelCase variable name
	// e.g., "gateway-access-methods" -> "infographicGatewayAccessMethodsData"
	function idToVarName(id) {
		// Convert kebab-case to PascalCase
		const pascalCase = id.split('-').map(word => 
			word.charAt(0).toUpperCase() + word.slice(1)
		).join('');
		// Return variable name: infographic + PascalCase + Data
		return 'infographic' + pascalCase + 'Data';
	}
	
	const varName = idToVarName(currentInfographicId);
	
	// Format as JavaScript variable
	const jsContent = `var ${varName} = ` + JSON.stringify(config, null, 2) + ';';
	
	// Generate filename based on infographic id
	const filename = `infographic-${currentInfographicId}-json.js`;
	
	const blob = new Blob([jsContent], { type: 'application/javascript' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	a.click();
	URL.revokeObjectURL(url);
}

