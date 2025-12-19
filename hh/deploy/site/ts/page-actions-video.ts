/**
 * PageActionsVideo - Mixin for video management actions (copy_video_app, move_video_app, delete_video_app, sort_video_app)
 */

import type { PageData } from './page-data.js';

export class PageActionsVideo {
  /**
   * Handler for copy_video_app: Copy video files to current page
   */
  async copy_video_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'video',
        initialPageId: pageId,
        overlayMode: 'pannable',
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'fileInstances' in result) {
            const videoResult = result as { fileIds: number[]; fileInstances: Array<{ file_id: number; source_page_id: number; source_rank: number }> };
            
            const browserOverlay = (browser as any).overlay;
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            if (!capturedDebugOptions) capturedDebugOptions = { debug: false, log: false };

            // Group by source page
            const bySource: Record<number, number[]> = {};
            videoResult.fileInstances.forEach(inst => {
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
                const response = await rpc.call('copy_video', params, capturedDebugOptions);
                if (response?.debug?.entries?.length) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'copy_video', params);
                }
                if (response?.data && browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'success' as const, text: `Copied video files from page ${sourcePageId}` }]
                  });
                }
              } catch (error) {
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const msg = error instanceof Error ? error.message : String(error);
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'error' as const, text: `Failed to copy video files from page ${sourcePageId}: ${msg}` }]
                  });
                }
                if (error && (error as any).debug?.entries?.length) {
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(error, 'copy_video', params);
                }
              }
            }

            return {
              _showMessage: `Completed copying ${videoResult.fileIds.length} video file(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('copy_video_app', error);
    }
  }

  /**
   * Handler for move_video_app: Move video files to current page
   */
  async move_video_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'video',
        initialPageId: pageId,
        overlayMode: 'pannable',
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'fileInstances' in result) {
            const videoResult = result as { fileIds: number[]; fileInstances: Array<{ file_id: number; source_page_id: number; source_rank: number }> };
            const browserOverlay = (browser as any).overlay;
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            if (!capturedDebugOptions) capturedDebugOptions = { debug: false, log: false };

            const bySource: Record<number, number[]> = {};
            videoResult.fileInstances.forEach(inst => {
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
                const response = await rpc.call('move_video', params, capturedDebugOptions);
                if (response?.debug?.entries?.length) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'move_video', params);
                }
                if (response?.data && browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'success' as const, text: `Moved video files from page ${sourcePageId}` }]
                  });
                }
              } catch (error) {
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const msg = error instanceof Error ? error.message : String(error);
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'error' as const, text: `Failed to move video files from page ${sourcePageId}: ${msg}` }]
                  });
                }
                if (error && (error as any).debug?.entries?.length) {
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(error, 'move_video', params);
                }
              }
            }

            return {
              _showMessage: `Completed moving ${videoResult.fileIds.length} video file(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('move_video_app', error);
    }
  }

  /**
   * Handler for delete_video_app: Delete video files from their source pages
   */
  async delete_video_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'video',
        initialPageId: pageId,
        overlayMode: 'pannable',
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'fileInstances' in result) {
            const videoResult = result as { fileIds: number[]; fileInstances: Array<{ file_id: number; source_page_id: number; source_rank: number }> };
            const browserOverlay = (browser as any).overlay;
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            if (!capturedDebugOptions) capturedDebugOptions = { debug: false, log: false };

            let hasDebugData = false;

            for (const instance of videoResult.fileInstances) {
              const params = {
                page_id: instance.source_page_id,
                video_id: instance.file_id,
                rank: instance.source_rank || undefined
              };
              try {
                const response = await rpc.call('remove_video', params, capturedDebugOptions);
                if (response?.debug?.entries?.length) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'remove_video', params);
                }
                if (response?.data && browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'success' as const, text: `Deleted video file ${instance.file_id} from page ${instance.source_page_id}` }]
                  });
                }
              } catch (error) {
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const msg = error instanceof Error ? error.message : String(error);
                  browserOverlay.setState({
                    messages: [...currentMessages, { type: 'error' as const, text: `Failed to delete video file ${instance.file_id}: ${msg}` }]
                  });
                }
                if (error && (error as any).debug?.entries?.length) {
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(error, 'remove_video', params);
                }
              }
            }

            return {
              _showMessage: `Completed deleting ${videoResult.fileIds.length} video file instance(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('delete_video_app', error);
    }
  }

  /**
   * Handler for sort_video_app: Sort/reorder video files on current page
   */
  async sort_video_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { VideoGroupSorter } = await import('./video-group-sorter.js');
      const sorter = new VideoGroupSorter(pageId);
      await sorter.show();
    } catch (error) {
      rpc.showError('sort_video_app', error);
    }
  }
}
