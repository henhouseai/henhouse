/**
 * ImageViewer - Image group viewer integrated with overlay system.
 * Uses OverlayManager for modal handling, provides pan/zoom/touch functionality.
 */
import { RPCClient } from './rpc-client.js';
import { OverlayManager } from './overlay/overlay-manager.js';
export class ImageViewer {
    constructor(pageId, initialImageId) {
        this.overlay = null;
        this.windowEl = null;
        this.headerEl = null;
        this.contentEl = null;
        this.footerEl = null;
        this.headerHeight = 0;
        this.footerHeight = 0;
        this.currentScale = 1;
        this.panX = 0;
        this.panY = 0;
        this.scaleForWidthMatch = 1;
        this.scaleForHeightMatch = 1;
        this.detentActive = false;
        this.resizeHandler = null;
        this.keyboardHandler = null;
        // Layout state
        this.baseOverlayWidth = 0;
        this.baseOverlayHeight = 0;
        this.totalExtraX = 0;
        this.totalExtraY = 0;
        this.baseInnerWidth = 0;
        this.baseInnerHeight = 0;
        this.intrinsicWidth = 0;
        this.intrinsicHeight = 0;
        this.pinchStartDist = null;
        this.pinchStartScale = 1;
        this.swipeStartX = null;
        this.swipeStartY = null;
        this.swipeStartTime = null;
        this.images = [];
        this.currentImageIndex = 0;
        // ---- Input handlers ----------------------------------------------------
        this.handleWheel = (e) => {
            e.preventDefault();
            const oldScale = this.currentScale;
            const sens = 0.1;
            const delta = e.deltaY < 0 ? sens : -sens;
            const newScale = oldScale + delta;
            this.applyScale(newScale, oldScale);
        };
        this.handleDragMove = (dx, dy) => {
            const state = this.getZoomState(this.currentScale);
            const widthHitsFirst = this.scaleForWidthMatch < this.scaleForHeightMatch;
            let newPanX = this.panX + dx;
            let newPanY = this.panY + dy;
            if (state === 'between') {
                if (widthHitsFirst) {
                    newPanY = 0;
                }
                else {
                    newPanX = 0;
                }
            }
            this.panX = newPanX;
            this.panY = newPanY;
            this.applyTransforms(this.currentScale);
        };
        this.rpc = new RPCClient();
        this.pageId = pageId;
        this.initialImageId = initialImageId;
    }
    async show() {
        await this.loadAndRender();
    }
    // ---- Data + Rendering --------------------------------------------------
    async loadAndRender() {
        try {
            const result = await this.rpc.call('get_image_group', { id: this.pageId });
            const groupData = result.data;
            if (!groupData || !groupData.images || groupData.images.length === 0) {
                throw new Error('No images found in image group');
            }
            this.images = groupData.images;
            if (this.initialImageId !== undefined) {
                const idx = this.images.findIndex(img => img.id === this.initialImageId);
                if (idx >= 0)
                    this.currentImageIndex = idx;
            }
            this.renderOverlay();
        }
        catch (err) {
            console.error('Error loading image viewer:', err);
            this.rpc.showError('image_viewer', err);
        }
    }
    renderOverlay() {
        const image = this.images[this.currentImageIndex];
        const instance = image.instances[image.instances.length - 1]; // largest
        this.intrinsicWidth = instance.width;
        this.intrinsicHeight = instance.height;
        // Create the image element
        const imageContainer = this.createImageElement(image, instance);
        // Create footer element for caption
        const footerEl = document.createElement('div');
        footerEl.className = 'image-viewer-caption';
        footerEl.textContent = image.caption || '';
        // Show overlay using OverlayManager
        const overlayManager = OverlayManager.getInstance();
        this.overlay = overlayManager.show({
            header: 'Image Viewer',
            content: [imageContainer],
            imageViewerMode: true,
            footerContent: footerEl,
            closable: true,
            showSubmit: false,
            cancelLabel: 'Close',
            className: 'image-viewer-overlay',
            onCancel: () => this.cleanup(),
            onUnmount: () => this.cleanupHandlers()
        });
        // Get references to overlay elements for pan/zoom
        this.windowEl = document.querySelector('.image-viewer-overlay');
        this.headerEl = this.windowEl?.querySelector('.contentWrapperHeader') || null;
        this.contentEl = this.windowEl?.querySelector('.contentWrapper') || null;
        this.footerEl = this.windowEl?.querySelector('.overlay-footer') || null;
        // Measure header and footer heights
        this.headerHeight = this.headerEl?.offsetHeight || 0;
        this.footerHeight = this.footerEl?.offsetHeight || 0;
        // Prevent body scroll while overlay is open
        document.body.style.overflow = 'hidden';
        // Initial sizing and inflection thresholds
        this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
        this.currentScale = 1;
        this.applyTransforms(1);
        this.bindEvents();
    }
    createImageElement(image, instance) {
        const box = document.createElement('div');
        box.id = 'imageViewerTargetImage';
        box.className = 'image-viewer-box';
        Object.assign(box.style, {
            boxSizing: 'border-box',
            width: '100%',
            height: '100%'
        });
        const img = document.createElement('img');
        img.id = 'imageViewerImg';
        img.className = 'image-viewer-img';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        const src = instance.src.startsWith('/srv/images/') ? instance.src : `/srv/images/${instance.src}`;
        img.src = src;
        img.alt = image.caption || '';
        box.appendChild(img);
        return box;
    }
    updateImageContent() {
        if (!this.contentEl)
            return;
        const image = this.images[this.currentImageIndex];
        const instance = image.instances[image.instances.length - 1]; // largest
        this.intrinsicWidth = instance.width;
        this.intrinsicHeight = instance.height;
        const img = this.contentEl.querySelector('#imageViewerImg');
        if (img) {
            const src = instance.src.startsWith('/srv/images/') ? instance.src : `/srv/images/${instance.src}`;
            img.src = src;
            img.alt = image.caption || '';
        }
        if (this.footerEl) {
            this.footerEl.textContent = image.caption || '';
        }
        this.currentScale = 1;
        this.panX = 0;
        this.panY = 0;
        this.detentActive = false;
        this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
        this.applyTransforms(1);
    }
    initializeBaseSizes(intrinsicW, intrinsicH) {
        if (!this.windowEl)
            return;
        // Temporarily size to intrinsic for measurement
        this.windowEl.style.width = `${intrinsicW}px`;
        this.windowEl.style.height = `${intrinsicH}px`;
        // Measure padding/border extras from computed style
        this.measureExtras();
        const vw = this.getPageWidth();
        const vh = this.getPageHeight();
        const margin = 200;
        const maxW = vw - margin;
        // Account for header and footer in available height
        const maxH = vh - margin - this.headerHeight - this.footerHeight;
        // Scale to fit viewport minus margin, preserving aspect
        const scaleX = (maxW - this.totalExtraX) / intrinsicW;
        const scaleY = (maxH - this.totalExtraY) / intrinsicH;
        const fitScale = Math.min(scaleX, scaleY, 1);
        this.baseInnerWidth = intrinsicW * fitScale;
        this.baseInnerHeight = intrinsicH * fitScale;
        this.baseOverlayWidth = this.baseInnerWidth + this.totalExtraX;
        // Add header and footer to total overlay height
        this.baseOverlayHeight = this.baseInnerHeight + this.totalExtraY + this.headerHeight + this.footerHeight;
        this.windowEl.style.width = `${this.baseOverlayWidth}px`;
        this.windowEl.style.height = `${this.baseOverlayHeight}px`;
        this.recomputeInflections();
    }
    recomputeInflections() {
        const vw = this.getPageWidth();
        const vh = this.getPageHeight();
        this.scaleForWidthMatch = vw / this.baseOverlayWidth;
        this.scaleForHeightMatch = vh / this.baseOverlayHeight;
    }
    measureExtras() {
        if (!this.windowEl)
            return;
        const cs = getComputedStyle(this.windowEl);
        const padX = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
        const padY = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
        const borderX = (parseFloat(cs.borderLeftWidth) || 0) + (parseFloat(cs.borderRightWidth) || 0);
        const borderY = (parseFloat(cs.borderTopWidth) || 0) + (parseFloat(cs.borderBottomWidth) || 0);
        this.totalExtraX = padX + borderX;
        this.totalExtraY = padY + borderY;
    }
    // ---- Transform and state ----------------------------------------------
    applyTransforms(scale) {
        if (!this.windowEl)
            return;
        const innerW = this.baseInnerWidth * scale;
        const innerH = this.baseInnerHeight * scale;
        const overlayW = innerW + this.totalExtraX;
        // Add header and footer heights to total overlay height
        const overlayH = innerH + this.totalExtraY + this.headerHeight + this.footerHeight;
        this.windowEl.style.width = `${overlayW}px`;
        this.windowEl.style.height = `${overlayH}px`;
        this.windowEl.style.maxWidth = `${overlayW}px`;
        this.windowEl.style.maxHeight = `${overlayH}px`;
        const clamped = this.clampPan(scale, this.panX, this.panY);
        this.panX = clamped.x;
        this.panY = clamped.y;
        this.windowEl.style.transform = `translate(-50%, -50%) translate(${this.panX}px, ${this.panY}px)`;
    }
    applyScale(newScale, oldScale) {
        const first = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
        // Cap so displayed pixels do not exceed 4x intrinsic
        const pixelPerDisplay = this.baseInnerWidth > 0 ? this.baseInnerWidth / this.intrinsicWidth : 1;
        const maxScale = Math.max(1, 4 / pixelPerDisplay);
        if (!this.detentActive && oldScale < first && newScale >= first) {
            newScale = first;
            this.detentActive = true;
        }
        else if (this.detentActive && newScale > first) {
            this.detentActive = false;
        }
        if (newScale < first) {
            this.detentActive = false;
        }
        newScale = Math.max(1, Math.min(maxScale, newScale));
        this.currentScale = newScale;
        const oldState = this.getZoomState(oldScale);
        const newState = this.getZoomState(newScale);
        if (oldState !== 'zoomedOut' && newState === 'zoomedOut') {
            this.panX = 0;
            this.panY = 0;
        }
        this.applyTransforms(newScale);
    }
    getZoomState(scale) {
        const first = Math.min(this.scaleForWidthMatch, this.scaleForHeightMatch);
        const second = Math.max(this.scaleForWidthMatch, this.scaleForHeightMatch);
        if (scale <= first + 1e-3)
            return 'zoomedOut';
        if (scale < second - 1e-3)
            return 'between';
        return 'zoomedIn';
    }
    clampPan(scale, panX, panY) {
        const state = this.getZoomState(scale);
        const vw = this.getPageWidth();
        const vh = this.getPageHeight();
        const scaledW = (this.baseInnerWidth * scale) + this.totalExtraX;
        const scaledH = (this.baseInnerHeight * scale) + this.totalExtraY;
        const halfOverflowX = Math.max(0, (scaledW - vw) / 2);
        const halfOverflowY = Math.max(0, (scaledH - vh) / 2);
        const widthHitsFirst = this.scaleForWidthMatch < this.scaleForHeightMatch;
        if (state === 'zoomedOut')
            return { x: 0, y: 0 };
        if (state === 'between') {
            if (widthHitsFirst) {
                return { x: Math.max(-halfOverflowX, Math.min(halfOverflowX, panX)), y: 0 };
            }
            return { x: 0, y: Math.max(-halfOverflowY, Math.min(halfOverflowY, panY)) };
        }
        return {
            x: Math.max(-halfOverflowX, Math.min(halfOverflowX, panX)),
            y: Math.max(-halfOverflowY, Math.min(halfOverflowY, panY))
        };
    }
    // ---- Events binding ----------------------------------------------------
    bindEvents() {
        if (!this.windowEl)
            return;
        // Wheel zoom on window
        this.windowEl.addEventListener('wheel', this.handleWheel, { passive: false });
        window.addEventListener('wheel', this.handleWheel, { passive: false });
        // Mouse drag for pan
        let dragging = false;
        let lastX = 0, lastY = 0;
        this.windowEl.addEventListener('mousedown', (e) => { e.preventDefault(); dragging = true; lastX = e.clientX; lastY = e.clientY; });
        this.windowEl.addEventListener('mouseup', () => { dragging = false; });
        this.windowEl.addEventListener('mouseleave', () => { dragging = false; });
        document.addEventListener('mouseup', () => { dragging = false; });
        document.addEventListener('mousemove', (e) => {
            if (!dragging)
                return;
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;
            lastX = e.clientX;
            lastY = e.clientY;
            this.handleDragMove(dx, dy);
        });
        // Touch handling: pinch zoom + drag pan
        const onPinchMove = (touches) => {
            if (touches.length !== 2 || this.pinchStartDist === null)
                return;
            const dist = this.getTouchDistance(touches);
            if (dist > 0) {
                const newScale = this.pinchStartScale * (dist / this.pinchStartDist);
                this.applyScale(newScale, this.currentScale);
            }
        };
        const startPinch = (e) => {
            this.pinchStartDist = this.getTouchDistance(e.touches);
            this.pinchStartScale = this.currentScale;
        };
        this.windowEl.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();
                startPinch(e);
                dragging = false;
                this.swipeStartX = null;
                this.swipeStartY = null;
                this.swipeStartTime = null;
            }
            else if (e.touches.length === 1) {
                const t = e.touches[0];
                lastX = t.clientX;
                lastY = t.clientY;
                dragging = true;
                this.swipeStartX = t.clientX;
                this.swipeStartY = t.clientY;
                this.swipeStartTime = e.timeStamp;
            }
        }, { passive: false });
        this.windowEl.addEventListener('touchmove', (e) => {
            if (e.touches.length === 1 && this.currentScale === 1) {
                e.preventDefault();
            }
            if (e.touches.length === 2) {
                e.preventDefault();
                dragging = false;
                if (this.pinchStartDist)
                    onPinchMove(e.touches);
                return;
            }
            if (!dragging)
                return;
            const t = e.touches[0];
            const dx = t.clientX - lastX;
            const dy = t.clientY - lastY;
            lastX = t.clientX;
            lastY = t.clientY;
            this.handleDragMove(dx, dy);
        }, { passive: false });
        this.windowEl.addEventListener('touchend', (e) => {
            dragging = false;
            // Swipe navigation: only when at default scale
            if (this.images.length > 1 && this.currentScale === 1 && this.swipeStartX !== null && this.swipeStartY !== null && this.swipeStartTime !== null) {
                const touch = e.changedTouches[0];
                const dx = touch.clientX - this.swipeStartX;
                const dy = touch.clientY - this.swipeStartY;
                const dt = e.timeStamp - this.swipeStartTime;
                const dist = Math.hypot(dx, dy);
                const isHorizontal = Math.abs(dx) > Math.abs(dy);
                const velocity = dt > 0 ? dist / dt : 0;
                const minSwipeDistance = 100;
                const minSwipeVelocity = 0.3;
                if (isHorizontal && (dist >= minSwipeDistance || velocity >= minSwipeVelocity)) {
                    if (dx > 0)
                        this.navigate(-1);
                    else
                        this.navigate(1);
                }
            }
            this.swipeStartX = null;
            this.swipeStartY = null;
            this.swipeStartTime = null;
            this.pinchStartDist = null;
        }, { passive: false });
        // Block scroll/zoom on backdrop
        const backdrop = document.querySelector('.overlay-backdrop');
        if (backdrop) {
            backdrop.addEventListener('wheel', this.handleWheel, { passive: false });
            backdrop.addEventListener('touchstart', (e) => {
                const te = e;
                if (te.touches.length === 2) {
                    e.preventDefault();
                    startPinch(te);
                }
            }, { passive: false });
            backdrop.addEventListener('touchmove', (e) => {
                const te = e;
                if (te.touches.length === 2) {
                    e.preventDefault();
                    onPinchMove(te.touches);
                }
            }, { passive: false });
            backdrop.addEventListener('touchend', () => {
                this.pinchStartDist = null;
            }, { passive: false });
        }
        // Global pinch for two-finger anywhere
        window.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();
                startPinch(e);
            }
        }, { passive: false });
        window.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();
                onPinchMove(e.touches);
            }
        }, { passive: false });
        window.addEventListener('touchend', () => {
            this.pinchStartDist = null;
        }, { passive: false });
        this.resizeHandler = () => {
            if (this.intrinsicWidth && this.intrinsicHeight) {
                this.initializeBaseSizes(this.intrinsicWidth, this.intrinsicHeight);
            }
            else {
                this.recomputeInflections();
            }
            this.currentScale = 1;
            this.panX = 0;
            this.panY = 0;
            this.detentActive = false;
            this.applyTransforms(1);
        };
        window.addEventListener('resize', this.resizeHandler);
        // Arrow keys for image navigation (ESC handled by overlay system)
        this.keyboardHandler = (e) => {
            if (!this.windowEl)
                return;
            if (e.key === 'ArrowLeft') {
                if (this.images.length > 1) {
                    this.navigate(-1);
                    e.preventDefault();
                }
            }
            else if (e.key === 'ArrowRight') {
                if (this.images.length > 1) {
                    this.navigate(1);
                    e.preventDefault();
                }
            }
        };
        document.addEventListener('keydown', this.keyboardHandler);
    }
    // ---- Utils -------------------------------------------------------------
    getPageWidth() {
        return window.innerWidth || document.documentElement.clientWidth;
    }
    getPageHeight() {
        return window.innerHeight || document.documentElement.clientHeight;
    }
    getTouchDistance(touches) {
        if (touches.length < 2)
            return 0;
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.hypot(dx, dy);
    }
    navigate(delta) {
        if (!this.images.length)
            return;
        this.currentImageIndex = (this.currentImageIndex + delta + this.images.length) % this.images.length;
        this.updateImageContent();
    }
    cleanupHandlers() {
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }
        if (this.keyboardHandler) {
            document.removeEventListener('keydown', this.keyboardHandler);
            this.keyboardHandler = null;
        }
        document.body.style.overflow = '';
    }
    cleanup() {
        this.cleanupHandlers();
        this.overlay = null;
        this.windowEl = null;
        this.headerEl = null;
        this.contentEl = null;
        this.footerEl = null;
    }
    static async openFromImageLink(pageId, imageId) {
        const viewer = new ImageViewer(pageId, imageId);
        await viewer.show();
    }
}
