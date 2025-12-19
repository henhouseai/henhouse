/**
 * AudioGroupSorter - table-only sorter for audio files on a page.
 */

import { OverlayManager } from './overlay/overlay-manager.js';
import { Overlay } from './overlay/overlay.js';
import { RPCClient } from './rpc-client.js';
import { handleRPCResponseWithDebug } from './debug-helper.js';
import './sortable.min.js';

declare global {
  interface Window {
    Sortable: any;
  }
}
const Sortable = (window as any).Sortable;

interface SetAudioRankResponse {
  page_id: number;
  audio_id: number;
  source_rank?: number;
  target_rank: number;
  audio?: Array<{
    id: number;
    audio_rank: number;
  }>;
}

export class AudioGroupSorter {
  private rpc: RPCClient;
  private overlay: Overlay | null = null;
  private pageId: number;
  private tableHtml: string = '';
  private currentRanks: Map<number, number> = new Map(); // audioId -> rank
  private desiredRanks: Map<number, number> = new Map(); // audioId -> desired rank
  private sortableTable: any = null;

  constructor(pageId: number) {
    this.rpc = new RPCClient();
    this.pageId = pageId;
  }

  async show(): Promise<void> {
    await this.loadAndRender();
  }

  private async loadAndRender(): Promise<void> {
    try {
      const tableResult = await this.rpc.call('get_page_section', {
        id: this.pageId,
        section: 'audio',
        view_type: 'table',
        overlay: 1
      });

      const tableData = tableResult.data?.dom_content;
      if (!tableData) {
        throw new Error('Failed to load audio group view');
      }

      this.tableHtml = tableData;
      this.extractInitialRanks();
      this.renderOverlay();
    } catch (error) {
      console.error('Error loading audio group sorter:', error);
      this.rpc.showError('audio_group_sorter', error);
    }
  }

  /**
   * Parse the table HTML and build the initial ranks map.
   * Expects table with rank in first column and ID in second column.
   */
  private extractInitialRanks(): void {
    this.currentRanks.clear();
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = this.tableHtml;
    const rows = tempDiv.querySelectorAll('table tbody tr');
    rows.forEach(row => {
      const cells = row.querySelectorAll('td');
      if (cells.length >= 2) {
        const rank = parseInt((cells[0].textContent || '').trim(), 10);
        const audioId = parseInt((cells[1].textContent || '').trim(), 10);
        if (!Number.isNaN(rank) && !Number.isNaN(audioId)) {
          this.currentRanks.set(audioId, rank);
        }
      }
    });
  }

  private renderOverlay(): void {
    const overlayManager = OverlayManager.getInstance();
    const content = [
      `
      <div class="content overlay" id="overlay_audio_group_sorter_table">
        ${this.tableHtml}
      </div>
    `
    ];

    this.overlay = overlayManager.show({
      header: `Sort Audio Files - Page ${this.pageId}`,
      content,
      contentHeaders: [''],
      mode: 'fixed',
      closable: true,
      showSubmit: true,
      submitLabel: 'Sort',
      cancelLabel: 'Cancel',
      onSubmit: async () => {
        return await this.handleSubmit();
      }
    });

    setTimeout(() => {
      this.prepareForSorting();
      this.setupSortable();
    }, 50);
  }

  /**
   * Add data-id attributes to table rows from the ID column.
   */
  private prepareForSorting(): void {
    const tableContainer = document.getElementById('overlay_audio_group_sorter_table');
    if (!tableContainer) return;
    const rows = tableContainer.querySelectorAll('table tbody tr');
    rows.forEach(row => {
      const cells = row.querySelectorAll('td');
      if (cells.length >= 2) {
        const audioId = parseInt((cells[1].textContent || '').trim(), 10);
        if (!Number.isNaN(audioId)) {
          (row as HTMLElement).setAttribute('data-id', audioId.toString());
        }
      }
    });
  }

  private setupSortable(): void {
    const tableContainer = document.getElementById('overlay_audio_group_sorter_table');
    if (!tableContainer) return;
    const tbody = tableContainer.querySelector('table tbody');
    if (!tbody) return;
    this.sortableTable = Sortable.create(tbody as HTMLElement, {
      animation: 150,
      dataIdAttr: 'data-id'
    });
  }

  private buildDesiredRanks(): void {
    this.desiredRanks.clear();
    if (!this.sortableTable) return;
    const order: number[] = this.sortableTable.toArray().map((id: string) => parseInt(id, 10));
    order.forEach((audioId, idx) => {
      if (!Number.isNaN(audioId)) {
        this.desiredRanks.set(audioId, idx + 1);
      }
    });
  }

  private async handleSubmit(): Promise<any> {
    if (!this.overlay) return;
    let capturedDebugOptions = this.overlay.getDebugOptions();
    if (!capturedDebugOptions) {
      capturedDebugOptions = { debug: false, log: false };
    }

    this.buildDesiredRanks();
    const desiredOrder = Array.from(this.desiredRanks.entries())
      .sort((a, b) => a[1] - b[1])
      .map(([audioId]) => audioId);

    if (desiredOrder.length === 0) {
      const currentMessages = (this.overlay as any)['state'].messages || [];
      this.overlay.setState({
        messages: [...currentMessages, { type: 'error' as const, text: 'No audio files found to sort' }]
      });
      return { _autoFade: false };
    }

    let hasDebugData = false;
    const maxIterations = desiredOrder.length;
    let iterationCount = 0;

    while (true) {
      iterationCount++;
      if (iterationCount > maxIterations) {
        const currentMessages = (this.overlay as any)['state'].messages || [];
        this.overlay.setState({
          messages: [...currentMessages, { type: 'error' as const, text: `Sorting failed: exceeded maximum iterations (${maxIterations}).` }]
        });
        return { _autoFade: false };
      }

      let maxDistance = 0;
      let audioToMove: { audioId: number; desiredRank: number; distance: number } | null = null;
      for (const [audioId, desiredRank] of this.desiredRanks.entries()) {
        const currentRank = this.currentRanks.get(audioId);
        if (currentRank === undefined) continue;
        if (currentRank === desiredRank) continue;
        const distance = Math.abs(currentRank - desiredRank);
        if (distance > maxDistance) {
          maxDistance = distance;
          audioToMove = { audioId, desiredRank, distance };
        }
      }

      if (!audioToMove || maxDistance === 0) {
        break;
      }

      try {
        const response = await this.rpc.call('set_audio_rank', {
          page_id: this.pageId,
          audio_id: audioToMove.audioId,
          target_rank: audioToMove.desiredRank
        }, capturedDebugOptions);

        if (response?.debug?.entries?.length) {
          hasDebugData = true;
          handleRPCResponseWithDebug(response, 'set_audio_rank', {
            page_id: this.pageId,
            audio_id: audioToMove.audioId,
            target_rank: audioToMove.desiredRank
          });
        }

        const responseData: SetAudioRankResponse = response.data;
        if (responseData?.audio?.length) {
          responseData.audio.forEach(a => this.currentRanks.set(a.id, a.audio_rank));
        } else {
          // Fallback: update current rank for moved audio only
          this.currentRanks.set(audioToMove.audioId, audioToMove.desiredRank);
        }

        const currentMessages = (this.overlay as any)['state'].messages || [];
        this.overlay.setState({
          messages: [...currentMessages, { type: 'success' as const, text: `Moved audio file ${audioToMove.audioId} to rank ${audioToMove.desiredRank}` }]
        });
      } catch (error) {
        const currentMessages = (this.overlay as any)['state'].messages || [];
        const msg = error instanceof Error ? error.message : String(error);
        this.overlay.setState({
          messages: [...currentMessages, { type: 'error' as const, text: `Failed to move audio file ${audioToMove.audioId}: ${msg}` }]
        });
        if (error && (error as any).debug?.entries?.length) {
          handleRPCResponseWithDebug(error, 'set_audio_rank', {
            page_id: this.pageId,
            audio_id: audioToMove.audioId,
            target_rank: audioToMove.desiredRank
          });
          hasDebugData = true;
        }
      }
    }

    return {
      _showMessage: 'Audio file order updated',
      _autoFade: !hasDebugData,
      _redirectAfterFade: hasDebugData ? null : 'self'
    };
  }
}
