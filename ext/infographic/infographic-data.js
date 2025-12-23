// Data loading and config management (core - used by both deploy and editor)

function loadConfig(config) {
	// Load glossary
	glossary = config.glossary || {};
	
	// Support both old format (single infographic) and new format (multiple)
	if (config.infographics && Array.isArray(config.infographics)) {
		// New format: multiple infographics
		allInfographics = config.infographics;
		// Deep copy positions to ensure proper restoration
		// Handle both old format (flat object with nodes) and new format (flat object with nodes + connections)
		allPositions = config.positions ? JSON.parse(JSON.stringify(config.positions)) : {};
		// Convert to new format (nodes/connections split) for internal use
		for (const infId in allPositions) {
			if (allPositions[infId] && !allPositions[infId].nodes && !allPositions[infId].connections) {
				// Old format: flat object - split into nodes and connections
				const flat = allPositions[infId];
				const nodes = {};
				const connections = {};
				for (const key in flat) {
					if (key.includes('->')) {
						connections[key] = flat[key];
					} else {
						nodes[key] = flat[key];
					}
				}
				allPositions[infId] = { nodes, connections };
			}
		}
		
		// Check if deploy mode (has specific infographic ID set)
		if (typeof window.infographicDeployId !== 'undefined' && window.infographicDeployId) {
			// Deploy mode: filter to only the requested infographic
			const requestedId = window.infographicDeployId;
			const filteredInfographic = allInfographics.find(inf => inf.id === requestedId);
			if (filteredInfographic) {
				allInfographics = [filteredInfographic]; // Only include the requested one
				currentInfographicId = filteredInfographic.id;
				nodes = filteredInfographic.nodes || [];
				connections = filteredInfographic.connections || [];
				// Restore saved positions for this infographic
				if (allPositions[currentInfographicId] && Object.keys(allPositions[currentInfographicId]).length > 0) {
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
			} else {
				console.warn(`Infographic with ID '${requestedId}' not found`);
			}
		} else if (allInfographics.length > 0) {
			// Editor mode: auto-select first infographic
			currentInfographicId = allInfographics[0].id;
			if (typeof switchInfographic === 'function') {
				// Editor mode: populate selector and switch
				const selector = document.getElementById('infographicSelector');
				if (selector) {
					selector.innerHTML = '<option value="">-- Select --</option>';
					allInfographics.forEach(infographic => {
						const option = document.createElement('option');
						option.value = infographic.id;
						option.textContent = infographic.title || infographic.id;
						selector.appendChild(option);
					});
					selector.value = currentInfographicId;
				}
				switchInfographic();
			} else {
				// Fallback: just set the first one directly
				const infographic = allInfographics[0];
				currentInfographicId = infographic.id;
				nodes = infographic.nodes || [];
				connections = infographic.connections || [];
				// Restore saved positions for this infographic
				if (allPositions[currentInfographicId] && Object.keys(allPositions[currentInfographicId]).length > 0) {
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
			}
		}
	} else {
		// Old format: single infographic (backward compatibility)
		allInfographics = [{
			id: config.title || 'default',
			title: config.title || 'Default Infographic',
			nodes: config.nodes || [],
			connections: config.connections || []
		}];
		allPositions = {};
		if (config.positions) {
			allPositions[allInfographics[0].id] = config.positions;
		}
		
		// Check if deploy mode (has specific infographic ID set)
		if (typeof window.infographicDeployId !== 'undefined' && window.infographicDeployId) {
			// Deploy mode: filter to only the requested infographic
			const requestedId = window.infographicDeployId;
			const filteredInfographic = allInfographics.find(inf => inf.id === requestedId);
			if (filteredInfographic) {
				allInfographics = [filteredInfographic]; // Only include the requested one
				currentInfographicId = filteredInfographic.id;
				nodes = filteredInfographic.nodes || [];
				connections = filteredInfographic.connections || [];
				if (allPositions[currentInfographicId]) {
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
			} else {
				console.warn(`Infographic with ID '${requestedId}' not found`);
			}
		} else {
			// Editor mode: populate selector and switch
			currentInfographicId = allInfographics[0].id;
			if (typeof switchInfographic === 'function') {
				const selector = document.getElementById('infographicSelector');
				if (selector) {
					selector.innerHTML = '<option value="">-- Select --</option>';
					allInfographics.forEach(infographic => {
						const option = document.createElement('option');
						option.value = infographic.id;
						option.textContent = infographic.title || infographic.id;
						selector.appendChild(option);
					});
					selector.value = currentInfographicId;
				}
				switchInfographic();
			} else {
				// Fallback: just set it directly
				const infographic = allInfographics[0];
				nodes = infographic.nodes || [];
				connections = infographic.connections || [];
				if (allPositions[currentInfographicId]) {
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
			}
		}
	}
}

