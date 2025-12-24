/**
 * PageActionsFiles - Mixin for file management actions (upload_files_app for now)
 */
import { getSeedData } from './seed.js';
export class PageActionsFiles {
    /**
     * Handler for upload_files_app: Upload files to current page
     */
    async upload_files_app(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        const { UploadHandler } = await import('./upload-handler.js');
        const handler = new UploadHandler(rpc, getSeedData(), 'file');
        await handler.handle();
    }
    /**
     * Handler for copy_files_app: Copy files to current page
     */
    async copy_files_app(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const { Browser } = await import('./browser.js');
            const browser = new Browser({
                mode: 'file',
                initialPageId: pageId,
                overlayMode: 'pannable',
                onSubmit: async (result) => {
                    if (typeof result === 'object' && 'fileInstances' in result) {
                        const fileResult = result;
                        const browserOverlay = browser.overlay;
                        let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
                        if (!capturedDebugOptions)
                            capturedDebugOptions = { debug: false, log: false };
                        // Group by source page
                        const bySource = {};
                        fileResult.fileInstances.forEach(inst => {
                            if (!bySource[inst.source_page_id])
                                bySource[inst.source_page_id] = [];
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
                                const response = await rpc.call('copy_files', params, capturedDebugOptions);
                                if (response?.debug?.entries?.length) {
                                    hasDebugData = true;
                                    const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                                    handleRPCResponseWithDebug(response, 'copy_files', params);
                                }
                                if (response?.data && browserOverlay) {
                                    const currentMessages = browserOverlay['state'].messages || [];
                                    browserOverlay.setState({
                                        messages: [...currentMessages, { type: 'success', text: `Copied files from page ${sourcePageId}` }]
                                    });
                                }
                            }
                            catch (error) {
                                if (browserOverlay) {
                                    const currentMessages = browserOverlay['state'].messages || [];
                                    const msg = error instanceof Error ? error.message : String(error);
                                    browserOverlay.setState({
                                        messages: [...currentMessages, { type: 'error', text: `Failed to copy files from page ${sourcePageId}: ${msg}` }]
                                    });
                                }
                                if (error && error.debug?.entries?.length) {
                                    const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                                    handleRPCResponseWithDebug(error, 'copy_files', params);
                                }
                            }
                        }
                        return {
                            _showMessage: `Completed copying ${fileResult.fileIds.length} file(s)`,
                            _autoFade: !hasDebugData,
                            _redirectAfterFade: hasDebugData ? null : 'self'
                        };
                    }
                }
            });
            await browser.show();
        }
        catch (error) {
            rpc.showError('copy_files_app', error);
        }
    }
    /**
     * Handler for move_files_app: Move files to current page
     */
    async move_files_app(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const { Browser } = await import('./browser.js');
            const browser = new Browser({
                mode: 'file',
                initialPageId: pageId,
                overlayMode: 'pannable',
                onSubmit: async (result) => {
                    if (typeof result === 'object' && 'fileInstances' in result) {
                        const fileResult = result;
                        const browserOverlay = browser.overlay;
                        let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
                        if (!capturedDebugOptions)
                            capturedDebugOptions = { debug: false, log: false };
                        const bySource = {};
                        fileResult.fileInstances.forEach(inst => {
                            if (!bySource[inst.source_page_id])
                                bySource[inst.source_page_id] = [];
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
                                const response = await rpc.call('move_files', params, capturedDebugOptions);
                                if (response?.debug?.entries?.length) {
                                    hasDebugData = true;
                                    const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                                    handleRPCResponseWithDebug(response, 'move_files', params);
                                }
                                if (response?.data && browserOverlay) {
                                    const currentMessages = browserOverlay['state'].messages || [];
                                    browserOverlay.setState({
                                        messages: [...currentMessages, { type: 'success', text: `Moved files from page ${sourcePageId}` }]
                                    });
                                }
                            }
                            catch (error) {
                                if (browserOverlay) {
                                    const currentMessages = browserOverlay['state'].messages || [];
                                    const msg = error instanceof Error ? error.message : String(error);
                                    browserOverlay.setState({
                                        messages: [...currentMessages, { type: 'error', text: `Failed to move files from page ${sourcePageId}: ${msg}` }]
                                    });
                                }
                                if (error && error.debug?.entries?.length) {
                                    const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                                    handleRPCResponseWithDebug(error, 'move_files', params);
                                }
                            }
                        }
                        return {
                            _showMessage: `Completed moving ${fileResult.fileIds.length} file(s)`,
                            _autoFade: !hasDebugData,
                            _redirectAfterFade: hasDebugData ? null : 'self'
                        };
                    }
                }
            });
            await browser.show();
        }
        catch (error) {
            rpc.showError('move_files_app', error);
        }
    }
    /**
     * Handler for delete_files_app: Delete files from their source pages
     */
    async delete_files_app(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const { Browser } = await import('./browser.js');
            const browser = new Browser({
                mode: 'file',
                initialPageId: pageId,
                overlayMode: 'pannable',
                onSubmit: async (result) => {
                    if (typeof result === 'object' && 'fileInstances' in result) {
                        const fileResult = result;
                        const browserOverlay = browser.overlay;
                        let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
                        if (!capturedDebugOptions)
                            capturedDebugOptions = { debug: false, log: false };
                        let hasDebugData = false;
                        for (const instance of fileResult.fileInstances) {
                            const params = {
                                page_id: instance.source_page_id,
                                file_id: instance.file_id,
                                rank: instance.source_rank || undefined
                            };
                            try {
                                const response = await rpc.call('remove_file', params, capturedDebugOptions);
                                if (response?.debug?.entries?.length) {
                                    hasDebugData = true;
                                    const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                                    handleRPCResponseWithDebug(response, 'remove_file', params);
                                }
                                if (response?.data && browserOverlay) {
                                    const currentMessages = browserOverlay['state'].messages || [];
                                    browserOverlay.setState({
                                        messages: [...currentMessages, { type: 'success', text: `Deleted file ${instance.file_id} from page ${instance.source_page_id}` }]
                                    });
                                }
                            }
                            catch (error) {
                                if (browserOverlay) {
                                    const currentMessages = browserOverlay['state'].messages || [];
                                    const msg = error instanceof Error ? error.message : String(error);
                                    browserOverlay.setState({
                                        messages: [...currentMessages, { type: 'error', text: `Failed to delete file ${instance.file_id}: ${msg}` }]
                                    });
                                }
                                if (error && error.debug?.entries?.length) {
                                    const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                                    handleRPCResponseWithDebug(error, 'remove_file', params);
                                }
                            }
                        }
                        return {
                            _showMessage: `Completed deleting ${fileResult.fileIds.length} file instance(s)`,
                            _autoFade: !hasDebugData,
                            _redirectAfterFade: hasDebugData ? null : 'self'
                        };
                    }
                }
            });
            await browser.show();
        }
        catch (error) {
            rpc.showError('delete_files_app', error);
        }
    }
    /**
     * Handler for sort_files_app: Sort/reorder files on current page (table mode)
     */
    async sort_files_app(rpc) {
        const pageId = this.id;
        if (!pageId) {
            alert('No page ID found');
            return;
        }
        try {
            const { FileGroupSorter } = await import('./file-group-sorter.js');
            const sorter = new FileGroupSorter(pageId);
            await sorter.show();
        }
        catch (error) {
            rpc.showError('sort_files_app', error);
        }
    }
}
