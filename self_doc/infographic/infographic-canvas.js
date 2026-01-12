// Canvas initialization and sizing

function updateContainerHeight() {
	const container = document.querySelector('.container');
	if (!container) return;
	
	// Expand container to fill entire viewport
	container.style.position = 'fixed';
	container.style.top = '0';
	container.style.left = '0';
	container.style.width = '100vw';
	container.style.height = '100vh';
	container.style.maxHeight = '100vh';
	container.style.margin = '0';
	container.style.padding = '0';
	
	// Prevent viewport scrolling
	document.body.style.overflow = 'hidden';
	document.documentElement.style.overflow = 'hidden';
}

function updateCanvasSize() {
	if (!canvas || !canvasContainer) return;
	
	// Get actual client dimensions (accounting for padding/borders)
	const containerWidth = canvasContainer.clientWidth;
	const containerHeight = canvasContainer.clientHeight;
	
	// Set canvas SVG dimensions to match container
	canvas.setAttribute('width', Math.max(1, containerWidth));
	canvas.setAttribute('height', Math.max(1, containerHeight));
}

function initializeCanvas() {
	// Initialize canvas references
	canvas = document.getElementById('canvas');
	if (!canvas) {
		console.error('Canvas element not found');
		return false;
	}
	canvasContainer = canvas.parentElement;
	
	// Set up container and canvas sizing
	updateContainerHeight();
	updateCanvasSize();
	
	window.addEventListener('resize', () => {
		updateContainerHeight();
		updateCanvasSize();
	});
	
	return true;
}

