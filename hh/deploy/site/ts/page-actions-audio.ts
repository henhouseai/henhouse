/**
 * PageActionsAudio - Mixin for audio management actions (copy_audio_app, move_audio_app, delete_audio_app, sort_audio_app)
 */

import type { PageData } from './page-data.js';

export class PageActionsAudio {
  /**
   * Handler for copy_audio_app: Copy audio files to current page
   */
  async copy_audio_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'audio',
        initialPageId: pageId,
        overlayMode: 'pannable',
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'fileInstances' in result) {
            const audioResult = result as { fileIds: number[]; fileInstances: Array<{ file_id: number; source_page_id: number; source_rank: number }> };
            
            const browserOverlay = (browser as any).overlay;
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            if (!capturedDebugOptions) capturedDebugOptions = { debug: false, log: false };

            // Group by source page
            const bySource: Record<number, number[]> = {};
            audioResult.fileInstances.forEach(inst => {
              if (!bySource[inst.source_page_id]) bySource[inst.source_page_id] = [];
              bySource[inst.source_page_id].push(inst.source_rank);
            });

            let hasDebugData = false;

            for (const [sourcePageIdStr, ranks] of Object.entries(bySource)) {
              const sourcePageId = parseInt(sourcePageIdStr, 10);
              const params = {
                source_page: sourcePageId,
                target_page: pageId,
                source_rank: ranks.join(',')
              };
              try {
                const response = await rpc.call('copy_audio', params, capturedDebugOptions);
                if (response?.debug?.entries?.length) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'copy_audio', params);
                }
                if (response?.data && browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'success' as const, text: `Copied audio files from page ${sourcePageId}` }]
                  });
                }
              } catch (error) {
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const msg = error instanceof Error ? error.message : String(error);
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'error' as const, text: `Failed to copy audio files from page ${sourcePageId}: ${msg}` }]
                  });
                }
                if (error && (error as any).debug?.entries?.length) {
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(error, 'copy_audio', params);
                }
              }
            }

            return {
              _showMessage: `Completed copying ${audioResult.fileIds.length} audio file(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('copy_audio_app', error);
    }
  }

  /**
   * Handler for move_audio_app: Move audio files to current page
   */
  async move_audio_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'audio',
        initialPageId: pageId,
        overlayMode: 'pannable',
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'fileInstances' in result) {
            const audioResult = result as { fileIds: number[]; fileInstances: Array<{ file_id: number; source_page_id: number; source_rank: number }> };
            const browserOverlay = (browser as any).overlay;
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            if (!capturedDebugOptions) capturedDebugOptions = { debug: false, log: false };

            const bySource: Record<number, number[]> = {};
            audioResult.fileInstances.forEach(inst => {
              if (!bySource[inst.source_page_id]) bySource[inst.source_page_id] = [];
              bySource[inst.source_page_id].push(inst.source_rank);
            });

            let hasDebugData = false;

            for (const [sourcePageIdStr, ranks] of Object.entries(bySource)) {
              const sourcePageId = parseInt(sourcePageIdStr, 10);
              const params = {
                source_page: sourcePageId,
                target_page: pageId,
                source_rank: ranks.join(',')
              };
              try {
                const response = await rpc.call('move_audio', params, capturedDebugOptions);
                if (response?.debug?.entries?.length) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'move_audio', params);
                }
                if (response?.data && browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'success' as const, text: `Moved audio files from page ${sourcePageId}` }]
                  });
                }
              } catch (error) {
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const msg = error instanceof Error ? error.message : String(error);
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'error' as const, text: `Failed to move audio files from page ${sourcePageId}: ${msg}` }]
                  });
                }
                if (error && (error as any).debug?.entries?.length) {
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(error, 'move_audio', params);
                }
              }
            }

            return {
              _showMessage: `Completed moving ${audioResult.fileIds.length} audio file(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('move_audio_app', error);
    }
  }

  /**
   * Handler for delete_audio_app: Delete audio files from their source pages
   */
  async delete_audio_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'audio',
        initialPageId: pageId,
        overlayMode: 'pannable',
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'fileInstances' in result) {
            const audioResult = result as { fileIds: number[]; fileInstances: Array<{ file_id: number; source_page_id: number; source_rank: number }> };
            const browserOverlay = (browser as any).overlay;
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            if (!capturedDebugOptions) capturedDebugOptions = { debug: false, log: false };

            let hasDebugData = false;

            for (const instance of audioResult.fileInstances) {
              const params = {
                page_id: instance.source_page_id,
                audio_id: instance.file_id,
                rank: instance.source_rank || undefined
              };
              try {
                const response = await rpc.call('remove_audio', params, capturedDebugOptions);
                if (response?.debug?.entries?.length) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'remove_audio', params);
                }
                if (response?.data && browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'success' as const, text: `Deleted audio file ${instance.file_id} from page ${instance.source_page_id}` }]
                  });
                }
              } catch (error) {
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const msg = error instanceof Error ? error.message : String(error);
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'error' as const, text: `Failed to delete audio file ${instance.file_id}: ${msg}` }]
                  });
                }
                if (error && (error as any).debug?.entries?.length) {
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(error, 'remove_audio', params);
                }
              }
            }

            return {
              _showMessage: `Completed deleting ${audioResult.fileIds.length} audio file instance(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('delete_audio_app', error);
    }
  }

  /**
   * Handler for sort_audio_app: Sort/reorder audio files on current page
   */
  async sort_audio_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { AudioGroupSorter } = await import('./audio-group-sorter.js');
      const sorter = new AudioGroupSorter(pageId);
      await sorter.show();
    } catch (error) {
      rpc.showError('sort_audio_app', error);
    }
  }
}
