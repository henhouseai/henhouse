/**
 * AudioViewer - Audio group viewer integrated with overlay system.
 * Simple overlay for audio playback with navigation between audio files.
 */
import { RPCClient } from './rpc-client.js';
import { OverlayManager } from './overlay/overlay-manager.js';
export class AudioViewer {
    constructor(pageId, initialAudioId) {
        this.overlay = null;
        this.audioFiles = [];
        this.currentAudioIndex = 0;
        this.audioElement = null;
        this.rpc = new RPCClient();
        this.pageId = pageId;
        this.initialAudioId = initialAudioId;
    }
    async show() {
        await this.loadAndRender();
    }
    async loadAndRender() {
        try {
            const result = await this.rpc.call('get_audio_group', { id: this.pageId });
            const groupData = result.data;
            if (!groupData || !groupData.audio || groupData.audio.length === 0) {
                throw new Error('No audio files found in audio group');
            }
            this.audioFiles = groupData.audio;
            if (this.initialAudioId !== undefined) {
                const idx = this.audioFiles.findIndex(audio => audio.id === this.initialAudioId);
                if (idx >= 0)
                    this.currentAudioIndex = idx;
            }
            this.renderOverlay();
        }
        catch (err) {
            console.error('Error loading audio viewer:', err);
            this.rpc.showError('audio_viewer', err);
        }
    }
    renderOverlay() {
        const audio = this.audioFiles[this.currentAudioIndex];
        // Find the best instance (prefer 'full', fallback to first)
        const fullInstance = audio.instances.find(inst => inst.instance_type === 'full');
        const instance = fullInstance || audio.instances[0];
        if (!instance) {
            throw new Error('No audio instance found');
        }
        // Create audio player element
        const audioContainer = this.createAudioElement(audio, instance);
        // Create footer element for caption and metadata
        const footerEl = document.createElement('div');
        footerEl.className = 'contentWrapperHeader overlay audio-viewer-footer';
        const captionLink = document.createElement('a');
        captionLink.className = 'audio-caption-link';
        captionLink.textContent = audio.caption || 'untitled';
        captionLink.href = `/audio/${audio.id}`;
        captionLink.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = captionLink.href;
        });
        const metadata = document.createElement('div');
        metadata.className = 'audio-metadata';
        const duration = audio.duration_seconds ? `${audio.duration_seconds.toFixed(1)}s` : 'N/A';
        const bitrate = audio.bitrate ? `${audio.bitrate} kbps` : 'N/A';
        metadata.textContent = `Duration: ${duration} | Bitrate: ${bitrate}`;
        footerEl.appendChild(captionLink);
        footerEl.appendChild(metadata);
        // Create navigation controls
        const navControls = this.createNavigationControls();
        // Combine content
        const content = [navControls, audioContainer];
        // Show overlay using OverlayManager
        const overlayManager = OverlayManager.getInstance();
        const currentAudio = this.audioFiles[this.currentAudioIndex];
        this.overlay = overlayManager.show({
            header: `Audio Viewer (${this.currentAudioIndex + 1} of ${this.audioFiles.length})`,
            content: content,
            footerContent: footerEl,
            closable: true,
            showSubmit: false,
            middleButtonLabel: 'More Info',
            middleButtonIndependent: true,
            cancelLabel: 'Close',
            mode: 'fixed',
            onCancel: () => this.cleanup(),
            onMiddleButton: () => {
                // Navigate to audio show page
                window.location.href = `/audio/${currentAudio.id}`;
            },
            onUnmount: () => this.cleanup()
        });
        // Prevent body scroll while overlay is open
        document.body.style.overflow = 'hidden';
    }
    createAudioElement(audio, instance) {
        const container = document.createElement('div');
        container.className = 'audio-viewer-container';
        container.style.padding = '20px';
        container.style.textAlign = 'center';
        // Create audio element
        const audioEl = document.createElement('audio');
        audioEl.controls = true;
        audioEl.style.width = '100%';
        audioEl.style.maxWidth = '600px';
        // Build stream URL from instance file_path
        // File path format: /srv/audio/{project}/YYYY/MM/DD/filename.ext
        // Stream URL: /audio/{id}/stream
        audioEl.src = `/audio/${audio.id}/stream`;
        audioEl.preload = 'metadata';
        this.audioElement = audioEl;
        container.appendChild(audioEl);
        return container;
    }
    createNavigationControls() {
        const navContainer = document.createElement('div');
        navContainer.className = 'audio-viewer-nav';
        navContainer.style.padding = '10px';
        navContainer.style.textAlign = 'center';
        navContainer.style.borderBottom = '1px solid #ccc';
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '← Previous';
        prevBtn.disabled = this.currentAudioIndex === 0;
        prevBtn.addEventListener('click', () => {
            if (this.currentAudioIndex > 0) {
                this.currentAudioIndex--;
                this.updateAudioContent();
            }
        });
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next →';
        nextBtn.disabled = this.currentAudioIndex >= this.audioFiles.length - 1;
        nextBtn.addEventListener('click', () => {
            if (this.currentAudioIndex < this.audioFiles.length - 1) {
                this.currentAudioIndex++;
                this.updateAudioContent();
            }
        });
        navContainer.appendChild(prevBtn);
        navContainer.appendChild(document.createTextNode(' '));
        navContainer.appendChild(nextBtn);
        return navContainer;
    }
    updateAudioContent() {
        if (!this.overlay || !this.audioElement)
            return;
        const audio = this.audioFiles[this.currentAudioIndex];
        // Find the best instance
        const fullInstance = audio.instances.find(inst => inst.instance_type === 'full');
        const instance = fullInstance || audio.instances[0];
        if (!instance)
            return;
        // Update audio source
        this.audioElement.src = `/audio/${audio.id}/stream`;
        this.audioElement.load();
        // Update header
        const headerEl = this.overlay.getHeaderElement ? this.overlay.getHeaderElement() : null;
        if (headerEl) {
            headerEl.textContent = `Audio Viewer (${this.currentAudioIndex + 1} of ${this.audioFiles.length})`;
        }
        // Update footer
        const footerEl = document.querySelector('.audio-viewer-footer');
        if (footerEl) {
            const captionLink = footerEl.querySelector('.audio-caption-link');
            const metadata = footerEl.querySelector('.audio-metadata');
            if (captionLink) {
                captionLink.textContent = audio.caption || 'untitled';
                captionLink.href = `/audio/${audio.id}`;
            }
            if (metadata) {
                const duration = audio.duration_seconds ? `${audio.duration_seconds.toFixed(1)}s` : 'N/A';
                const bitrate = audio.bitrate ? `${audio.bitrate} kbps` : 'N/A';
                metadata.textContent = `Duration: ${duration} | Bitrate: ${bitrate}`;
            }
        }
        // Update navigation buttons
        const prevBtn = document.querySelector('.audio-viewer-nav button:first-child');
        const nextBtn = document.querySelector('.audio-viewer-nav button:last-child');
        if (prevBtn)
            prevBtn.disabled = this.currentAudioIndex === 0;
        if (nextBtn)
            nextBtn.disabled = this.currentAudioIndex >= this.audioFiles.length - 1;
        // Update middle button (More Info) to point to current audio
        const middleBtn = document.querySelector('#middleOverlayWindow');
        if (middleBtn) {
            // Remove old listeners and add new one
            const newMiddleBtn = middleBtn.cloneNode(true);
            middleBtn.parentNode?.replaceChild(newMiddleBtn, middleBtn);
            newMiddleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = `/audio/${audio.id}`;
            });
        }
    }
    cleanup() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement = null;
        }
        document.body.style.overflow = '';
    }
    static async openFromAudioLink(pageId, audioId) {
        const viewer = new AudioViewer(pageId, audioId);
        await viewer.show();
    }
}
