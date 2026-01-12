// Main initialization and orchestration

function initialize() {
	// Editor mode: Set sidebar to collapsed by default
	if (typeof toggleControls === 'function') {
		const container = document.querySelector('.container');
		const toggleBtn = document.getElementById('toggleControlsBtn');
		if (container) {
			container.classList.add('controls-collapsed');
			if (toggleBtn) {
				toggleBtn.textContent = '▶';
				toggleBtn.title = 'Expand Controls';
			}
		}
		
		// Show grid controls only in editor mode
		const gridToggleBtn = document.getElementById('gridToggleBtn');
		if (gridToggleBtn) {
			gridToggleBtn.style.display = 'flex';
		}
	}
	
	// Initialize canvas
	if (!initializeCanvas()) {
		return;
	}
	
	// Initialize panning
	initializePanning();
	
	// Merge all infographic data sources
	let mergedData = {
		infographics: [],
		positions: {},
		glossary: {}
	};
	
	// Merge glossary data if available
	if (typeof infographicGlossaryData !== 'undefined' && infographicGlossaryData.glossary) {
		mergedData.glossary = Object.assign({}, infographicGlossaryData.glossary);
	}
	
	// Merge all infographic data files (each uses a unique variable name)
	// Dynamically discover all variables matching pattern: infographic*Data
	const dataSources = [];
	
	// Scan window object for infographic data variables
	// Pattern: infographic + PascalCase + Data (e.g., infographicGatewayAccessMethodsData)
	for (const key in window) {
		if (key.startsWith('infographic') && key.endsWith('Data') && typeof window[key] === 'object' && window[key] !== null) {
			dataSources.push(window[key]);
		}
	}
	
	// Sort data sources to prioritize project-folder-hierarchy first
	// Extract infographic IDs to determine order
	dataSources.sort((a, b) => {
		const aId = a.infographics && a.infographics[0] ? a.infographics[0].id : '';
		const bId = b.infographics && b.infographics[0] ? b.infographics[0].id : '';
		
		// Put project-folder-hierarchy first
		if (aId === 'project-folder-hierarchy') return -1;
		if (bId === 'project-folder-hierarchy') return 1;
		
		// Otherwise maintain original order
		return 0;
	});
	
	dataSources.forEach(data => {
		if (!data) return;
		
		if (data.infographics && Array.isArray(data.infographics)) {
			mergedData.infographics.push(...data.infographics);
		}
		if (data.positions) {
			mergedData.positions = Object.assign({}, mergedData.positions, data.positions);
		}
		if (data.glossary) {
			mergedData.glossary = Object.assign({}, mergedData.glossary, data.glossary);
		}
	});
	
	// Load merged data if we have any infographics
	if (mergedData.infographics.length > 0 || Object.keys(mergedData.glossary).length > 0) {
		// Wait a moment to ensure canvas is properly sized
		setTimeout(() => {
			loadConfig(mergedData);
			// After loading, render and zoom to fit (works for both modes)
			setTimeout(() => {
				if (typeof render === 'function') {
					render();
				}
				if (typeof zoomToFit === 'function') {
					setTimeout(() => {
						zoomToFit();
						// Fade out startup overlay after zoom completes
						setTimeout(() => {
							fadeOutStartupOverlay();
						}, 200);
					}, 100);
				} else {
					fadeOutStartupOverlay();
				}
			}, 100);
		}, 100);
	} else {
		// Editor mode: show message in selector
		const selector = document.getElementById('infographicSelector');
		if (selector) {
			selector.innerHTML = '<option value="">-- No data found --</option>';
		}
		// Still fade out overlay even if no data
		setTimeout(() => {
			fadeOutStartupOverlay();
		}, 500);
	}
	
	// Editor mode: Build lists after a short delay to ensure DOM is ready
	setTimeout(() => {
		if (typeof buildHighLevelGlossaryList === 'function') {
			buildHighLevelGlossaryList();
			buildConceptsList();
			buildDetailsList();
			buildConnectionsList();
			buildConnectionDetailsList();
			buildGlossaryList();
			buildOrphansList();
			buildUnknownsList();
		}
	}, 200);
}

function fadeOutStartupOverlay() {
	const overlay = document.getElementById('startupOverlay');
	if (overlay) {
		overlay.classList.add('fade-out');
		// After fade completes, trigger resize and zoom to fit
		setTimeout(() => {
			overlay.classList.add('hidden');
			// Update container height (editor mode) if function exists
			if (typeof updateContainerHeight === 'function') {
				updateContainerHeight();
			}
			// Update canvas size
			if (typeof updateCanvasSize === 'function') {
				updateCanvasSize();
			}
			// Trigger resize event to recalculate canvas size
			if (window.dispatchEvent) {
				window.dispatchEvent(new Event('resize'));
			}
			// Zoom to fit after resize
			if (typeof zoomToFit === 'function') {
				setTimeout(() => {
					zoomToFit();
				}, 50);
			}
		}, 800);
	}
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
	// DOM hasn't finished loading yet
	document.addEventListener('DOMContentLoaded', initialize);
} else {
	// DOM is already loaded
	initialize();
}

