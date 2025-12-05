/**
 * ImageViewer - Full-screen image viewer overlay with pan/zoom support.
 * Ported from legacy/core/js/image.js
 */
import { OverlayManager } from './overlay/overlay-manager.js';
import { RPCClient } from './rpc-client.js';
// Import interact.js as a side-effect (it will be available as window.interact)
import './interact.min.js';
const interact = window.interact;
export class ImageViewer {
    constructor(pageId, initialImageId) {
        this.overlay = null;
        this.images = [];
        this.currentImageIndex = 0;
        this.touchStartX = null;
        this.touchStartY = null;
        this.keyboardHandler = null;
        this.resizeHandler = null;
        this.interactInstance = null;
        this.rpc = new RPCClient();
        this.pageId = pageId;
        this.initialImageId = initialImageId;
    }
    /**
     * Show the image viewer overlay.
     */
    async show() {
        await this.loadAndRender();
    }
    /**
     * Load image group data and render overlay.
     */
    async loadAndRender() {
        try {
            // Call get_image_group MCP tool (accepts either 'id' or 'page_id')
            const result = await this.rpc.call('get_image_group', { id: this.pageId });
            const groupData = result.data;
            if (!groupData || !groupData.images || groupData.images.length === 0) {
                throw new Error('No images found in image group');
            }
            this.images = groupData.images;
            // Find initial image index if provided
            if (this.initialImageId !== undefined) {
                const index = this.images.findIndex(img => img.id === this.initialImageId);
                if (index >= 0) {
                    this.currentImageIndex = index;
                }
            }
            // Render overlay
            this.renderOverlay();
        }
        catch (error) {
            console.error('Error loading image viewer:', error);
            this.rpc.showError('image_viewer', error);
        }
    }
    /**
     * Get the best image instance for a given target width.
     * Ported from legacy getBestInstance logic.
     */
    getBestInstance(targetWidth, instances) {
        if (!instances || instances.length === 0) {
            return null;
        }
        // Instances are already sorted by width (ascending) from backend
        // Find the first instance that is >= targetWidth, or use the largest
        let best = instances[0];
        for (let i = 1; i < instances.length; i++) {
            if (instances[i].width >= targetWidth) {
                best = instances[i];
                break;
            }
        }
        // If we didn't find one >= targetWidth, use the largest (last one)
        if (best.width < targetWidth && instances.length > 0) {
            best = instances[instances.length - 1];
        }
        return best;
    }
    /**
     * Calculate display dimensions for an image instance.
     * Ported from legacy getImage logic.
     */
    calculateDisplayDimensions(instance, maxWidth, maxHeight) {
        let w = instance.width;
        let h = instance.height;
        // Scale down if necessary
        if (w > maxWidth) {
            h = h * (maxWidth / w);
            w = maxWidth;
        }
        if (h > maxHeight) {
            w = w * (maxHeight / h);
            h = maxHeight;
        }
        // Further scaling for tall narrow images
        if (h > maxWidth * 1.5) {
            w = (maxWidth * w * 1.5) / h;
            h = maxWidth * 1.5;
        }
        return {
            width: Math.round(w),
            height: Math.round(h)
        };
    }
    /**
     * Render the overlay with current image.
     */
    renderOverlay() {
        if (this.images.length === 0) {
            return;
        }
        const currentImage = this.images[this.currentImageIndex];
        const pageWidth = this.getPageWidth();
        const pageHeight = this.getPageHeight();
        const maxOverlayWidth = pageWidth - 40;
        const maxOverlayHeight = pageHeight - 40;
        const maxImageWidth = maxOverlayWidth - 40;
        const maxImageHeight = maxOverlayHeight - 80;
        // Get best instance for display
        const displayInstance = this.getBestInstance(maxImageWidth, currentImage.instances);
        if (!displayInstance) {
            console.error('No display instance found');
            return;
        }
        // Calculate display dimensions
        const displayDims = this.calculateDisplayDimensions(displayInstance, maxImageWidth, maxImageHeight);
        const imageWidth = displayDims.width;
        const imageHeight = displayDims.height;
        const overlayWidth = imageWidth + 40;
        const overlayHeight = imageHeight + 80;
        // Build HTML
        const imageHtml = `
      <div id="imageViewerTargetImageWrapper">
        <div id="imageZoomContainer">
          <img id="imageViewerTargetImage" src="${displayInstance.src}" alt="${currentImage.caption}" width="${imageWidth}" height="${imageHeight}">
        </div>
      </div>
    `;
        let controlLinks = '<div id="imageViewerControlLinks">';
        if (this.images.length > 1) {
            controlLinks += `<a id="retargetImageViewerToPreviousLink">&lt;&lt;</a>`;
            controlLinks += `${this.currentImageIndex + 1}/${this.images.length}`;
            controlLinks += `<a id="retargetImageViewerToNextLink">&gt;&gt;</a>`;
        }
        controlLinks += '<a id="closeImageViewerLink">close</a>';
        controlLinks += '</div>';
        let visibilityString = '<div id="imageViewerVisibility">';
        switch (currentImage.visibility.toString()) {
            case '-1':
                visibilityString += 'PRIVATE';
                break;
            case '0':
                visibilityString += 'HIDDEN';
                break;
            default:
                // Public - no label
                break;
        }
        visibilityString += '</div>';
        const captionHtml = `<div id="imageViewerCaption">${currentImage.caption}</div>`;
        // Preload full-size image (largest instance, which is last in sorted array)
        const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
        const preloadImg = new Image();
        preloadImg.src = fullSizeInstance.src;
        const overlayManager = OverlayManager.getInstance();
        this.overlay = overlayManager.show({
            header: '',
            content: [imageHtml + visibilityString + captionHtml + controlLinks],
            contentHeaders: [''],
            closable: true,
            showSubmit: false,
            onCancel: () => {
                this.cleanup();
            }
        });
        // Get the overlay window element
        const windowEl = this.overlay.windowEl;
        if (!windowEl) {
            console.error('Could not find overlay window element');
            return;
        }
        // Set overlay dimensions
        windowEl.style.width = `${overlayWidth}px`;
        windowEl.style.height = `${overlayHeight}px`;
        windowEl.style.marginLeft = `${-overlayWidth / 2}px`;
        windowEl.style.marginTop = `${-overlayHeight / 2}px`;
        // Set image wrapper dimensions
        const imageWrapper = windowEl.querySelector('#imageViewerTargetImageWrapper');
        if (imageWrapper) {
            imageWrapper.style.width = `${imageWidth}px`;
            imageWrapper.style.height = `${imageHeight}px`;
        }
        // Set caption and control links width
        const caption = windowEl.querySelector('#imageViewerCaption');
        const controlLinksEl = windowEl.querySelector('#imageViewerControlLinks');
        if (caption)
            caption.style.width = `${overlayWidth - 36}px`;
        if (controlLinksEl)
            controlLinksEl.style.width = `${overlayWidth - 36}px`;
        // Set up interact.js after a short delay
        setTimeout(() => {
            this.setupInteract();
            this.setupEventHandlers(windowEl);
            this.bindKeys();
        }, 50);
    }
    /**
     * Set up interact.js for pan/zoom.
     */
    setupInteract() {
        const zoomContainer = document.getElementById('imageZoomContainer');
        if (!zoomContainer) {
            return;
        }
        // Initialize transform data
        zoomContainer.dataset.scale = '1';
        zoomContainer.dataset.x = '0';
        zoomContainer.dataset.y = '0';
        zoomContainer.dataset.fullsize = 'false';
        // Set initial transform
        zoomContainer.style.transform = 'scale(1)';
        zoomContainer.style.transformOrigin = 'center center';
        // Set up interact.js
        this.interactInstance = interact(zoomContainer)
            .gesturable({
            listeners: {
                start: (event) => this.onGestureStart(event),
                move: (event) => this.onGestureMove(event),
                end: (event) => this.onGestureEnd(event)
            }
        })
            .draggable({
            inertia: true,
            modifiers: [
                interact.modifiers.restrict({
                    restriction: 'parent',
                    endOnly: true
                })
            ],
            listeners: {
                move: (event) => this.dragMoveListener(event)
            }
        });
    }
    /**
     * Set up event handlers for navigation and controls.
     */
    setupEventHandlers(windowEl) {
        // Previous/Next navigation
        const prevLink = windowEl.querySelector('#retargetImageViewerToPreviousLink');
        const nextLink = windowEl.querySelector('#retargetImageViewerToNextLink');
        const closeLink = windowEl.querySelector('#closeImageViewerLink');
        if (prevLink) {
            prevLink.addEventListener('click', () => {
                this.navigateImage(-1);
            });
        }
        if (nextLink) {
            nextLink.addEventListener('click', () => {
                this.navigateImage(1);
            });
        }
        if (closeLink) {
            closeLink.addEventListener('click', () => {
                this.cleanup();
            });
        }
        // Touch handlers for swipe navigation
        const imageWrapper = windowEl.querySelector('#imageViewerTargetImageWrapper');
        if (imageWrapper) {
            imageWrapper.addEventListener('touchstart', (e) => this.handleTouchStart(e));
            imageWrapper.addEventListener('touchmove', (e) => this.handleTouchMove(e));
            imageWrapper.addEventListener('touchend', (e) => this.handleTouchEnd(e));
        }
        // Wheel zoom
        if (imageWrapper) {
            imageWrapper.addEventListener('wheel', (e) => this.handleWheelZoom(e));
        }
        // Window resize handler
        this.resizeHandler = () => {
            this.navigateImage(0); // Re-render with new dimensions
        };
        window.addEventListener('resize', this.resizeHandler);
    }
    /**
     * Navigate to a different image.
     */
    navigateImage(increment) {
        if (this.images.length === 0) {
            return;
        }
        // Update index
        this.currentImageIndex = (this.currentImageIndex + increment + this.images.length) % this.images.length;
        // Re-render overlay
        this.renderOverlay();
    }
    /**
     * Handle touch start for swipe detection.
     */
    handleTouchStart(event) {
        const touch = event.touches[0];
        this.touchStartX = touch.clientX;
        this.touchStartY = touch.clientY;
    }
    /**
     * Handle touch move - prevent scrolling if not zoomed.
     */
    handleTouchMove(event) {
        const zoomContainer = document.getElementById('imageZoomContainer');
        if (!zoomContainer)
            return;
        const scale = parseFloat(zoomContainer.dataset.scale) || 1;
        if (scale === 1) {
            // Only prevent default scrolling if not zoomed in
            event.preventDefault();
        }
    }
    /**
     * Handle touch end - detect swipe gestures.
     */
    handleTouchEnd(event) {
        const zoomContainer = document.getElementById('imageZoomContainer');
        if (!zoomContainer)
            return;
        const scale = parseFloat(zoomContainer.dataset.scale) || 1;
        if (scale === 1 && this.touchStartX !== null && this.touchStartY !== null) {
            const touch = event.changedTouches[0];
            const touchEndX = touch.clientX;
            const touchEndY = touch.clientY;
            const deltaX = touchEndX - this.touchStartX;
            const deltaY = touchEndY - this.touchStartY;
            // Check if the swipe is horizontal and long enough
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    // Swipe right - go to previous image
                    if (this.images.length > 1) {
                        this.navigateImage(-1);
                    }
                }
                else {
                    // Swipe left - go to next image
                    if (this.images.length > 1) {
                        this.navigateImage(1);
                    }
                }
            }
        }
        // Reset touch positions
        this.touchStartX = null;
        this.touchStartY = null;
    }
    /**
     * Handle wheel zoom.
     */
    handleWheelZoom(event) {
        event.preventDefault();
        const zoomContainer = document.getElementById('imageZoomContainer');
        if (!zoomContainer)
            return;
        let scale = parseFloat(zoomContainer.dataset.scale) || 1;
        // Load full-size image if not already loaded
        if (!zoomContainer.dataset.fullsize || zoomContainer.dataset.fullsize === 'false') {
            const currentImage = this.images[this.currentImageIndex];
            const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
            const img = zoomContainer.querySelector('img');
            if (img) {
                img.src = fullSizeInstance.src;
            }
            zoomContainer.dataset.fullsize = 'true';
        }
        const zoomSensitivity = 0.1;
        const delta = event.deltaY;
        if (delta < 0) {
            scale += zoomSensitivity;
        }
        else {
            scale -= zoomSensitivity;
        }
        const minScale = 1;
        const maxScale = 3; // 300% of full size
        scale = Math.max(minScale, Math.min(maxScale, scale));
        zoomContainer.dataset.scale = scale.toString();
        zoomContainer.style.transformOrigin = 'center center';
        zoomContainer.style.transform = `scale(${scale})`;
    }
    /**
     * Interact.js gesture start handler.
     */
    onGestureStart(event) {
        const target = event.target;
        const dataset = target.dataset;
        // Load full-size image if not already loaded (when pinch-to-zoom starts)
        if (!dataset.fullsize || dataset.fullsize === 'false') {
            const currentImage = this.images[this.currentImageIndex];
            // Full-size is the largest instance (last in sorted ascending array)
            const fullSizeInstance = currentImage.instances[currentImage.instances.length - 1];
            const img = target.querySelector('img');
            if (img) {
                img.src = fullSizeInstance.src;
            }
            dataset.fullsize = 'true';
        }
        // Store initial scale and position
        dataset.initialScale = dataset.scale || '1';
        dataset.initialX = dataset.x || '0';
        dataset.initialY = dataset.y || '0';
    }
    /**
     * Interact.js gesture move handler.
     */
    onGestureMove(event) {
        event.preventDefault();
        const target = event.target;
        const dataset = target.dataset;
        const initialScale = parseFloat(dataset.initialScale) || 1;
        let scale = initialScale * event.scale;
        const minScale = 1;
        const maxScale = 3;
        scale = Math.max(minScale, Math.min(maxScale, scale));
        dataset.scale = scale.toString();
        const initialX = parseFloat(dataset.initialX) || 0;
        const initialY = parseFloat(dataset.initialY) || 0;
        const x = initialX + event.deltaX;
        const y = initialY + event.deltaY;
        // Calculate boundaries
        const imageWidth = target.offsetWidth * scale;
        const imageHeight = target.offsetHeight * scale;
        const containerWidth = target.parentElement.offsetWidth;
        const containerHeight = target.parentElement.offsetHeight;
        const maxX = Math.max(0, (imageWidth - containerWidth) / 2);
        const maxY = Math.max(0, (imageHeight - containerHeight) / 2);
        const constrainedX = Math.max(-maxX, Math.min(x, maxX));
        const constrainedY = Math.max(-maxY, Math.min(y, maxY));
        dataset.x = constrainedX.toString();
        dataset.y = constrainedY.toString();
        target.style.transform = `translate(${constrainedX}px, ${constrainedY}px) scale(${scale})`;
        target.style.transformOrigin = 'center center';
    }
    /**
     * Interact.js gesture end handler.
     */
    onGestureEnd(event) {
        this.dragMoveListener(event);
    }
    /**
     * Interact.js drag move listener.
     */
    dragMoveListener(event) {
        const target = event.target;
        const dataset = target.dataset;
        let x = (parseFloat(dataset.x) || 0) + event.dx;
        let y = (parseFloat(dataset.y) || 0) + event.dy;
        const scale = parseFloat(dataset.scale) || 1;
        // Get dimensions
        const imageWidth = target.offsetWidth * scale;
        const imageHeight = target.offsetHeight * scale;
        const containerWidth = target.parentElement.offsetWidth;
        const containerHeight = target.parentElement.offsetHeight;
        // Calculate boundaries
        const maxX = Math.max(0, (imageWidth - containerWidth) / 2);
        const maxY = Math.max(0, (imageHeight - containerHeight) / 2);
        // Constrain x and y
        x = Math.max(-maxX, Math.min(x, maxX));
        y = Math.max(-maxY, Math.min(y, maxY));
        // Update position data
        dataset.x = x.toString();
        dataset.y = y.toString();
        // Apply transform
        target.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    }
    /**
     * Bind keyboard shortcuts.
     */
    bindKeys() {
        this.keyboardHandler = (event) => {
            switch (event.keyCode || event.which) {
                case 27: // Esc
                    this.cleanup();
                    event.preventDefault();
                    break;
                case 37: // Left Arrow
                    if (this.images.length > 1) {
                        this.navigateImage(-1);
                        event.preventDefault();
                    }
                    break;
                case 39: // Right Arrow
                    if (this.images.length > 1) {
                        this.navigateImage(1);
                        event.preventDefault();
                    }
                    break;
            }
        };
        document.addEventListener('keydown', this.keyboardHandler);
    }
    /**
     * Unbind keyboard shortcuts.
     */
    unbindKeys() {
        if (this.keyboardHandler) {
            document.removeEventListener('keydown', this.keyboardHandler);
            this.keyboardHandler = null;
        }
    }
    /**
     * Get page width (viewport width).
     */
    getPageWidth() {
        return window.innerWidth || document.documentElement.clientWidth;
    }
    /**
     * Get page height (viewport height).
     */
    getPageHeight() {
        return window.innerHeight || document.documentElement.clientHeight;
    }
    /**
     * Cleanup and close the viewer.
     */
    cleanup() {
        this.unbindKeys();
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }
        if (this.interactInstance) {
            this.interactInstance.unset();
            this.interactInstance = null;
        }
        if (this.overlay) {
            // Overlay cleanup is handled by OverlayManager
            this.overlay = null;
        }
    }
    /**
     * Static factory method to open viewer from an image link.
     */
    static async openFromImageLink(pageId, imageId) {
        const viewer = new ImageViewer(pageId, imageId);
        await viewer.show();
    }
}
