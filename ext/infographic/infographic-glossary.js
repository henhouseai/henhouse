// Glossary lookup and modal functionality

function getGlossaryTitle(termId) {
	if (!termId) return termId;
	const term = glossary[termId];
	return term ? term.title : termId.replace(/_/g, ' ');
}

function getGlossaryDescription(termId) {
	if (!termId) return '';
	const term = glossary[termId];
	return term ? term.description : '';
}

function getGlossaryPageId(termId) {
	if (!termId) return null;
	const term = glossary[termId];
	return term && term.page_id ? term.page_id : null;
}

// Helper functions for parsing lowLevel items (supports both string and object formats)
function parseLowLevelItem(item) {
	// Handle string format (backward compatible)
	if (typeof item === 'string') {
		return {
			display: getGlossaryTitle(item),
			term: item,
			hasGlossary: !!getGlossaryDescription(item)
		};
	}
	
	// Handle object format: { term: "glossary_term", display: "Display Text" }
	if (typeof item === 'object' && item !== null) {
		const term = item.term || '';
		const termTitle = term ? getGlossaryTitle(term) : '';
		const display = item.display || '';
		
		// If both term and display exist, format as "Term Title: Display"
		// Otherwise use the old behavior for backward compatibility
		if (term && display) {
			return {
				termTitle: termTitle,
				term: term,
				display: display,
				hasGlossary: term ? !!getGlossaryDescription(term) : false,
				hasDisplayText: true
			};
		} else {
			// Backward compatibility: if no display, use term title as display
			return {
				display: display || termTitle || term,
				term: term,
				hasGlossary: term ? !!getGlossaryDescription(term) : false,
				hasDisplayText: false
			};
		}
	}
	
	// Fallback for invalid formats
	return {
		display: String(item),
		term: '',
		hasGlossary: false
	};
}

function showGlossaryModal(termId) {
	const desc = getGlossaryDescription(termId);
	if (!desc) return;
	
	// Stop any active dragging
	if (draggedNode) {
		stopDrag();
	}
	
	const title = getGlossaryTitle(termId);
	document.getElementById('glossaryModalTitle').textContent = title;
	document.getElementById('glossaryModalDescription').textContent = desc;
	
	// Handle page link button
	const pageId = getGlossaryPageId(termId);
	const pageLinkBtn = document.getElementById('glossaryModalPageLink');
	if (pageLinkBtn) {
		if (pageId) {
			// Show button if page_id exists (for visual confirmation)
			pageLinkBtn.style.display = 'flex';
			
			// Set up link if helper function is available, otherwise make it non-functional
			if (typeof window.hh !== 'undefined' && typeof window.hh.get_link === 'function') {
				// Functional link: set href and allow navigation
				const link = window.hh.get_link(pageId);
				pageLinkBtn.href = link;
				pageLinkBtn.onclick = function(e) {
					// Allow normal link navigation
					dismissGlossaryModal();
				};
			} else {
				// Non-functional link: show button but prevent navigation
				pageLinkBtn.href = '#';
				pageLinkBtn.onclick = function(e) {
					e.preventDefault();
					e.stopPropagation();
					// Button shows but does nothing (visual confirmation only)
				};
			}
		} else {
			// Hide button if no page_id
			pageLinkBtn.style.display = 'none';
		}
	}
	
	const overlay = document.getElementById('glossaryOverlay');
	overlay.style.display = 'flex';
	glossaryModalOpen = true;
	
	// Prevent body scroll
	document.body.style.overflow = 'hidden';
}

function dismissGlossaryModal(e) {
	// If event is provided, check if clicking on overlay (not modal content)
	if (e && e.target !== e.currentTarget) {
		// If clicking on close button, dismiss
		if (e.target.classList.contains('close-button')) {
			// Continue to dismiss
		} else {
			// Clicking inside modal content, don't dismiss
			return;
		}
	}
	
	const overlay = document.getElementById('glossaryOverlay');
	overlay.style.display = 'none';
	glossaryModalOpen = false;
	
	// Restore body scroll
	document.body.style.overflow = '';
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
	if (e.key === 'Escape' && glossaryModalOpen) {
		dismissGlossaryModal();
	}
});

