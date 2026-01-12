// Editor-only data functions (glossary list building)
// This file is only loaded in editor mode (HTML file), not deployed

function buildHighLevelGlossaryList() {
	const highLevelContent = document.getElementById('highLevelGlossaryContent');
	if (!highLevelContent) return;
	
	// Check if we have infographics
	if (!allInfographics || allInfographics.length === 0) {
		highLevelContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No infographics available</div>';
		return;
	}
	
	// Clear existing content
	highLevelContent.innerHTML = '';
	
	// For each infographic, find matching glossary term by title
	allInfographics.forEach(infographic => {
		const infographicTitle = infographic.title;
		
		// Find glossary term that matches this title
		let matchingTermId = null;
		for (const termId in glossary) {
			if (glossary[termId].title === infographicTitle) {
				matchingTermId = termId;
				break;
			}
		}
		
		// Always show the infographic, even if no glossary entry exists
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		item.innerHTML = '<span class="term-name">' + infographicTitle + '</span>';
		
		if (matchingTermId) {
			// Found matching glossary term - make it clickable
			item.addEventListener('click', () => {
				showGlossaryModal(matchingTermId);
			});
		} else {
			// No glossary entry - show but don't make clickable
			item.style.opacity = '0.6';
		}
		
		highLevelContent.appendChild(item);
	});
}

function buildConceptsList() {
	const conceptsContent = document.getElementById('conceptsListContent');
	if (!conceptsContent) return;
	
	// Check if we have infographics
	if (!allInfographics || allInfographics.length === 0) {
		conceptsContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No infographics available</div>';
		return;
	}
	
	// Collect all unique node labels (concepts) from all infographics
	const conceptSet = new Set();
	allInfographics.forEach(infographic => {
		(infographic.nodes || []).forEach(node => {
			if (node.label) {
				conceptSet.add(node.label);
			}
		});
	});
	
	// Convert to array and sort
	const concepts = Array.from(conceptSet).sort();
	
	// Clear existing content
	conceptsContent.innerHTML = '';
	
	// Build list items
	concepts.forEach(termId => {
		const term = glossary[termId];
		const title = term ? term.title : getGlossaryTitle(termId);
		const desc = getGlossaryDescription(termId);
		
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		item.innerHTML = '<span class="term-name">' + title + '</span>';
		if (desc) {
			item.addEventListener('click', () => {
				showGlossaryModal(termId);
			});
		}
		conceptsContent.appendChild(item);
	});
}

function buildDetailsList() {
	const detailsContent = document.getElementById('detailsListContent');
	if (!detailsContent) return;
	
	// Check if we have infographics
	if (!allInfographics || allInfographics.length === 0) {
		detailsContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No infographics available</div>';
		return;
	}
	
	// Collect all unique lowLevel items (details) from all nodes in all infographics
	const detailSet = new Set();
	allInfographics.forEach(infographic => {
		(infographic.nodes || []).forEach(node => {
			(node.lowLevel || []).forEach(item => {
				// Extract term from item (supports both string and object formats)
				const term = typeof item === 'string' ? item : (item.term || '');
				if (term) {
					detailSet.add(term);
				}
			});
		});
	});
	
	// Convert to array and sort
	const details = Array.from(detailSet).sort();
	
	// Clear existing content
	detailsContent.innerHTML = '';
	
	// Build list items
	details.forEach(termId => {
		const term = glossary[termId];
		const title = term ? term.title : getGlossaryTitle(termId);
		const desc = getGlossaryDescription(termId);
		
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		item.innerHTML = '<span class="term-name">' + title + '</span>';
		if (desc) {
			item.addEventListener('click', () => {
				showGlossaryModal(termId);
			});
		}
		detailsContent.appendChild(item);
	});
}

function buildConnectionsList() {
	const connectionsContent = document.getElementById('connectionsListContent');
	if (!connectionsContent) return;
	
	// Check if we have infographics
	if (!allInfographics || allInfographics.length === 0) {
		connectionsContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No infographics available</div>';
		return;
	}
	
	// Collect all unique connection descriptions from all infographics
	const connectionSet = new Set();
	allInfographics.forEach(infographic => {
		(infographic.connections || []).forEach(conn => {
			if (conn.description) {
				connectionSet.add(conn.description);
			}
		});
	});
	
	// Convert to array and sort
	const connections = Array.from(connectionSet).sort();
	
	// Clear existing content
	connectionsContent.innerHTML = '';
	
	// Build list items
	connections.forEach(termId => {
		const term = glossary[termId];
		const title = term ? term.title : getGlossaryTitle(termId);
		const desc = getGlossaryDescription(termId);
		
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		item.innerHTML = '<span class="term-name">' + title + '</span>';
		if (desc) {
			item.addEventListener('click', () => {
				showGlossaryModal(termId);
			});
		}
		connectionsContent.appendChild(item);
	});
}

function buildConnectionDetailsList() {
	const connectionDetailsContent = document.getElementById('connectionDetailsListContent');
	if (!connectionDetailsContent) return;
	
	// Check if we have infographics
	if (!allInfographics || allInfographics.length === 0) {
		connectionDetailsContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No infographics available</div>';
		return;
	}
	
	// Collect all unique lowLevel items from all connections in all infographics
	const connectionDetailSet = new Set();
	allInfographics.forEach(infographic => {
		(infographic.connections || []).forEach(conn => {
			(conn.lowLevel || []).forEach(item => {
				// Extract term from item (supports both string and object formats)
				const term = typeof item === 'string' ? item : (item.term || '');
				if (term) {
					connectionDetailSet.add(term);
				}
			});
		});
	});
	
	// Convert to array and sort
	const connectionDetails = Array.from(connectionDetailSet).sort();
	
	// Clear existing content
	connectionDetailsContent.innerHTML = '';
	
	// Build list items
	connectionDetails.forEach(termId => {
		const term = glossary[termId];
		const title = term ? term.title : getGlossaryTitle(termId);
		const desc = getGlossaryDescription(termId);
		
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		item.innerHTML = '<span class="term-name">' + title + '</span>';
		if (desc) {
			item.addEventListener('click', () => {
				showGlossaryModal(termId);
			});
		}
		connectionDetailsContent.appendChild(item);
	});
}

// Shared function to count glossary term occurrences
function countGlossaryTerms() {
	const termCounts = {};
	
	// Initialize counts for all glossary terms
	if (glossary) {
		Object.keys(glossary).forEach(termId => {
			termCounts[termId] = 0;
		});
	}
	
	// Count occurrences in all infographics
	(allInfographics || []).forEach(infographic => {
		// Count in node labels
		(infographic.nodes || []).forEach(node => {
			if (node.label && termCounts.hasOwnProperty(node.label)) {
				termCounts[node.label]++;
			}
			// Count in lowLevel items
			(node.lowLevel || []).forEach(item => {
				// Extract term from item (supports both string and object formats)
				const term = typeof item === 'string' ? item : (item.term || '');
				if (term && termCounts.hasOwnProperty(term)) {
					termCounts[term]++;
				}
			});
		});
		
		// Count in connection descriptions and lowLevel items
		(infographic.connections || []).forEach(conn => {
			if (conn.description && termCounts.hasOwnProperty(conn.description)) {
				termCounts[conn.description]++;
			}
			// Count in connection lowLevel items
			(conn.lowLevel || []).forEach(item => {
				// Extract term from item (supports both string and object formats)
				const term = typeof item === 'string' ? item : (item.term || '');
				if (term && termCounts.hasOwnProperty(term)) {
					termCounts[term]++;
				}
			});
		});
	});
	
	return termCounts;
}

function buildGlossaryList() {
	const glossaryContent = document.getElementById('glossaryListContent');
	if (!glossaryContent) return;
	
	// Check if glossary exists
	if (!glossary || Object.keys(glossary).length === 0) {
		glossaryContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No glossary available</div>';
		return;
	}
	
	// Count how many times each glossary term appears
	const termCounts = countGlossaryTerms();
	
	// Build sorted list (by title)
	const sortedTerms = Object.keys(glossary).sort((a, b) => {
		const titleA = getGlossaryTitle(a).toLowerCase();
		const titleB = getGlossaryTitle(b).toLowerCase();
		return titleA.localeCompare(titleB);
	});
	
	// Create HTML
	glossaryContent.innerHTML = '';
	sortedTerms.forEach(termId => {
		const term = glossary[termId];
		const count = termCounts[termId] || 0;
		
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		item.innerHTML = '<span class="term-name">' + term.title + '</span><span class="term-count">(' + count + ')</span>';
		item.addEventListener('click', () => {
			showGlossaryModal(termId);
		});
		
		glossaryContent.appendChild(item);
	});
}

function buildOrphansList() {
	const orphansContent = document.getElementById('orphansListContent');
	if (!orphansContent) {
		console.error('orphansListContent element not found');
		return;
	}
	
	// Check if glossary exists
	if (!glossary || Object.keys(glossary).length === 0) {
		orphansContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No glossary available</div>';
		return;
	}
	
	// Count how many times each glossary term appears (reuse same logic)
	const termCounts = countGlossaryTerms();
	
	// Filter to only terms with 0 count (orphans)
	const orphans = Object.keys(glossary).filter(termId => {
		return (termCounts[termId] || 0) === 0;
	});
	
	// Sort by title
	const sortedOrphans = orphans.sort((a, b) => {
		const titleA = getGlossaryTitle(a).toLowerCase();
		const titleB = getGlossaryTitle(b).toLowerCase();
		return titleA.localeCompare(titleB);
	});
	
	// Create HTML
	orphansContent.innerHTML = '';
	if (sortedOrphans.length === 0) {
		orphansContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No orphans found</div>';
		return;
	}
	
	sortedOrphans.forEach(termId => {
		const term = glossary[termId];
		
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		item.innerHTML = '<span class="term-name">' + term.title + '</span>';
		item.addEventListener('click', () => {
			showGlossaryModal(termId);
		});
		
		orphansContent.appendChild(item);
	});
}

function buildUnknownsList() {
	const unknownsContent = document.getElementById('unknownsListContent');
	if (!unknownsContent) {
		return;
	}
	
	// Check if glossary exists (same pattern as orphans)
	if (!glossary || Object.keys(glossary).length === 0) {
		unknownsContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No glossary available</div>';
		return;
	}
	
	// Check if infographics exist
	if (!allInfographics || allInfographics.length === 0) {
		unknownsContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No infographics available</div>';
		return;
	}
	
	// Collect all terms used in infographics
	const usedTermsSet = new Set();
	
	(allInfographics || []).forEach(infographic => {
		// Collect node labels
		(infographic.nodes || []).forEach(node => {
			if (node.label) {
				usedTermsSet.add(node.label);
			}
			// Collect lowLevel items (both string and object formats)
			(node.lowLevel || []).forEach(item => {
				const term = typeof item === 'string' ? item : (item.term || '');
				if (term) {
					usedTermsSet.add(term);
				}
			});
		});
		
		// Collect connection descriptions
		(infographic.connections || []).forEach(conn => {
			if (conn.description) {
				usedTermsSet.add(conn.description);
			}
			// Collect connection lowLevel items (both string and object formats)
			(conn.lowLevel || []).forEach(item => {
				const term = typeof item === 'string' ? item : (item.term || '');
				if (term) {
					usedTermsSet.add(term);
				}
			});
		});
	});
	
	// Filter to only terms that don't have glossary entries (unknowns)
	const unknowns = Array.from(usedTermsSet).filter(term => {
		return !glossary || !glossary[term];
	});
	
	// Sort by term ID (lowercase)
	const sortedUnknowns = unknowns.sort((a, b) => {
		return a.toLowerCase().localeCompare(b.toLowerCase());
	});
	
	// Create HTML (same pattern as orphans)
	unknownsContent.innerHTML = '';
	if (sortedUnknowns.length === 0) {
		unknownsContent.innerHTML = '<div style="color: #666; font-size: 11px; padding: 5px;">No unknowns found</div>';
		return;
	}
	
	sortedUnknowns.forEach(termId => {
		const item = document.createElement('div');
		item.className = 'glossary-list-item';
		// Display as dead text (no click handler, styled differently)
		const displayText = termId.replace(/_/g, ' ');
		item.innerHTML = '<span class="term-name" style="color: #999; cursor: default;">' + displayText + '</span>';
		// No click handler - it's dead text
		
		unknownsContent.appendChild(item);
	});
}

