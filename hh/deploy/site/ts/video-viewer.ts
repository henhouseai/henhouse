/**
 * VideoViewer - Video group viewer integrated with overlay system.
 * Simple overlay for video playback with navigation between video files.
 */

import { RPCClient } from './rpc-client.js';
import { OverlayManager } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';

interface VideoInstance {
  instance_type: string;
  file_path: string;
  mime_type: string;
  size_bytes: number;
  width?: number;
  height?: number;
  duration_seconds?: number;
  bitrate?: number;
}

interface VideoData {
  id: number;
  caption: string;
  visibility: number;
  viewCount: number;
  uploaded?: string;
  mime_type: string;
  width?: number;
  height?: number;
  duration_seconds?: number;
  bitrate?: number;
  instances: VideoInstance[];
}

interface VideoGroupResponse {
  page_id: number;
  video: VideoData[];
}

export class VideoViewer {
  private rpc: RPCClient;
  private overlay: Overlay | null = null;
  private pageId: number;
  private initialVideoId?: number;
  private videoFiles: VideoData[] = [];
  private currentVideoIndex = 0;
  private videoElement: HTMLVideoElement | null = null;

  constructor(pageId: number, initialVideoId?: number) {
    this.rpc = new RPCClient();
    this.pageId = pageId;
    this.initialVideoId = initialVideoId;
  }

  async show(): Promise<void> {
    await this.loadAndRender();
  }

  private async loadAndRender(): Promise<void> {
    try {
      const result = await this.rpc.call('get_video_group', { id: this.pageId });
      const groupData = result.data as VideoGroupResponse;
      if (!groupData || !groupData.video || groupData.video.length === 0) {
        throw new Error('No video files found in video group');
      }
      this.videoFiles = groupData.video;
      if (this.initialVideoId !== undefined) {
        const idx = this.videoFiles.findIndex(video => video.id === this.initialVideoId);
        if (idx >= 0) this.currentVideoIndex = idx;
      }
      this.renderOverlay();
    } catch (err) {
      console.error('Error loading video viewer:', err);
      this.rpc.showError('video_viewer', err);
    }
  }

  private renderOverlay(): void {
    const video = this.videoFiles[this.currentVideoIndex];
    
    // Find the best instance (prefer 'full', fallback to first)
    const fullInstance = video.instances.find(inst => inst.instance_type === 'full');
    const instance = fullInstance || video.instances[0];
    
    if (!instance) {
      throw new Error('No video instance found');
    }

    // Create video player element
    const videoContainer = this.createVideoElement(video, instance);

    // Create footer element for caption and metadata
    const footerEl = document.createElement('div');
    footerEl.className = 'contentWrapperHeader overlay video-viewer-footer';
    
    const captionLink = document.createElement('a');
    captionLink.className = 'video-caption-link';
    captionLink.textContent = video.caption || 'untitled';
    captionLink.href = `/video/${video.id}`;
    captionLink.addEventListener('click', (e) => {
      e.preventDefault();
      window.location.href = captionLink.href;
    });
    
    const metadata = document.createElement('div');
    metadata.className = 'video-metadata';
    const dimensions = video.width && video.height ? `${video.width}x${video.height}` : 'N/A';
    const duration = video.duration_seconds ? `${video.duration_seconds.toFixed(1)}s` : 'N/A';
    const bitrate = video.bitrate ? `${video.bitrate} kbps` : 'N/A';
    metadata.textContent = `Dimensions: ${dimensions} | Duration: ${duration} | Bitrate: ${bitrate}`;
    
    footerEl.appendChild(captionLink);
    footerEl.appendChild(metadata);

    // Create navigation controls
    const navControls = this.createNavigationControls();

    // Combine content
    const content = [navControls, videoContainer];

    // Show overlay using OverlayManager
    const overlayManager = OverlayManager.getInstance();
    const currentVideo = this.videoFiles[this.currentVideoIndex];
    this.overlay = overlayManager.show({
      header: `Video Viewer (${this.currentVideoIndex + 1} of ${this.videoFiles.length})`,
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
        // Navigate to video show page
        window.location.href = `/video/${currentVideo.id}`;
      },
      onUnmount: () => this.cleanup()
    });

    // Prevent body scroll while overlay is open
    document.body.style.overflow = 'hidden';
  }

  private createVideoElement(video: VideoData, instance: VideoInstance): HTMLElement {
    const container = document.createElement('div');
    container.className = 'video-viewer-container';
    container.style.padding = '20px';
    container.style.textAlign = 'center';

    // Create video element
    const videoEl = document.createElement('video');
    videoEl.controls = true;
    videoEl.style.width = '100%';
    videoEl.style.maxWidth = '800px';
    videoEl.style.maxHeight = '600px';
    
    // Build stream URL from instance file_path
    // File path format: /srv/video/{project}/YYYY/MM/DD/filename.ext
    // Stream URL: /video/{id}/stream
    videoEl.src = `/video/${video.id}/stream`;
    videoEl.preload = 'metadata';

    // Set dimensions if available
    if (instance.width && instance.height) {
      videoEl.width = instance.width;
      videoEl.height = instance.height;
    }

    this.videoElement = videoEl;
    container.appendChild(videoEl);

    return container;
  }

  private createNavigationControls(): HTMLElement {
    const navContainer = document.createElement('div');
    navContainer.className = 'video-viewer-nav';
    navContainer.style.padding = '10px';
    navContainer.style.textAlign = 'center';
    navContainer.style.borderBottom = '1px solid #ccc';

    const prevBtn = document.createElement('button');
    prevBtn.textContent = '← Previous';
    prevBtn.disabled = this.currentVideoIndex === 0;
    prevBtn.addEventListener('click', () => {
      if (this.currentVideoIndex > 0) {
        this.currentVideoIndex--;
        this.updateVideoContent();
      }
    });

    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Next →';
    nextBtn.disabled = this.currentVideoIndex >= this.videoFiles.length - 1;
    nextBtn.addEventListener('click', () => {
      if (this.currentVideoIndex < this.videoFiles.length - 1) {
        this.currentVideoIndex++;
        this.updateVideoContent();
      }
    });

    navContainer.appendChild(prevBtn);
    navContainer.appendChild(document.createTextNode(' '));
    navContainer.appendChild(nextBtn);

    return navContainer;
  }

  private updateVideoContent(): void {
    if (!this.overlay || !this.videoElement) return;

    const video = this.videoFiles[this.currentVideoIndex];
    
    // Find the best instance
    const fullInstance = video.instances.find(inst => inst.instance_type === 'full');
    const instance = fullInstance || video.instances[0];
    
    if (!instance) return;

    // Update video source
    this.videoElement.src = `/video/${video.id}/stream`;
    if (instance.width && instance.height) {
      this.videoElement.width = instance.width;
      this.videoElement.height = instance.height;
    }
    this.videoElement.load();

    // Update header
    const headerEl = this.overlay.getHeaderElement ? this.overlay.getHeaderElement() : null;
    if (headerEl) {
      headerEl.textContent = `Video Viewer (${this.currentVideoIndex + 1} of ${this.videoFiles.length})`;
    }

    // Update footer
    const footerEl = document.querySelector('.video-viewer-footer') as HTMLElement;
    if (footerEl) {
      const captionLink = footerEl.querySelector('.video-caption-link') as HTMLAnchorElement;
      const metadata = footerEl.querySelector('.video-metadata') as HTMLElement;
      
      if (captionLink) {
        captionLink.textContent = video.caption || 'untitled';
        captionLink.href = `/video/${video.id}`;
      }
      
      if (metadata) {
        const dimensions = video.width && video.height ? `${video.width}x${video.height}` : 'N/A';
        const duration = video.duration_seconds ? `${video.duration_seconds.toFixed(1)}s` : 'N/A';
        const bitrate = video.bitrate ? `${video.bitrate} kbps` : 'N/A';
        metadata.textContent = `Dimensions: ${dimensions} | Duration: ${duration} | Bitrate: ${bitrate}`;
      }
    }

    // Update navigation buttons
    const prevBtn = document.querySelector('.video-viewer-nav button:first-child') as HTMLButtonElement;
    const nextBtn = document.querySelector('.video-viewer-nav button:last-child') as HTMLButtonElement;
    if (prevBtn) prevBtn.disabled = this.currentVideoIndex === 0;
    if (nextBtn) nextBtn.disabled = this.currentVideoIndex >= this.videoFiles.length - 1;

    // Update middle button (More Info) to point to current video
    const middleBtn = document.querySelector('#middleOverlayWindow') as HTMLAnchorElement;
    if (middleBtn) {
      // Remove old listeners and add new one
      const newMiddleBtn = middleBtn.cloneNode(true) as HTMLAnchorElement;
      middleBtn.parentNode?.replaceChild(newMiddleBtn, middleBtn);
      newMiddleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = `/video/${video.id}`;
      });
    }
  }

  private cleanup(): void {
    if (this.videoElement) {
      this.videoElement.pause();
      this.videoElement = null;
    }
    document.body.style.overflow = '';
  }

  static async openFromVideoLink(pageId: number, videoId?: number): Promise<void> {
    const viewer = new VideoViewer(pageId, videoId);
    await viewer.show();
  }
}
