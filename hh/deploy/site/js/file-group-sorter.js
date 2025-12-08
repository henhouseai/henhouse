/**
 * FileGroupSorter - table-only sorter for files on a page.
 */
import { OverlayManager } from './overlay/overlay-manager.js';
import { RPCClient } from './rpc-client.js';
import { handleRPCResponseWithDebug } from './debug-helper.js';
import './sortable.min.js';
const Sortable = window.Sortable;
export class FileGroupSorter {
    constructor(pageId) {
        this.overlay = null;
        this.tableHtml = '';
        this.currentRanks = new Map(); // fileId -> rank
        this.desiredRanks = new Map(); // fileId -> desired rank
        this.sortableTable = null;
        this.rpc = new RPCClient();
        this.pageId = pageId;
    }
    async show() {
        await this.loadAndRender();
    }
    async loadAndRender() {
        try {
            const tableResult = await this.rpc.call('get_page_section', {
                id: this.pageId,
                section: 'files',
                view_type: 'table',
                overlay: 1
            });
            const tableData = tableResult.data?.dom_content;
            if (!tableData) {
                throw new Error('Failed to load file group view');
            }
            this.tableHtml = tableData;
            this.extractInitialRanks();
            this.renderOverlay();
        }
        catch (error) {
            console.error('Error loading file group sorter:', error);
            this.rpc.showError('file_group_sorter', error);
        }
    }
    /**
     * Parse the table HTML and build the initial ranks map.
     * Expects table with rank in first column and ID in second column.
     */
    extractInitialRanks() {
        this.currentRanks.clear();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = this.tableHtml;
        const rows = tempDiv.querySelectorAll('table tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 2) {
                const rank = parseInt((cells[0].textContent || '').trim(), 10);
                const fileId = parseInt((cells[1].textContent || '').trim(), 10);
                if (!Number.isNaN(rank) && !Number.isNaN(fileId)) {
                    this.currentRanks.set(fileId, rank);
                }
            }
        });
    }
    renderOverlay() {
        const overlayManager = OverlayManager.getInstance();
        const content = [
            `
      <div class="content overlay" id="overlay_file_group_sorter_table">
        ${this.tableHtml}
      </div>
    `
        ];
        this.overlay = overlayManager.show({
            header: `Sort Files - Page ${this.pageId}`,
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
    prepareForSorting() {
        const tableContainer = document.getElementById('overlay_file_group_sorter_table');
        if (!tableContainer)
            return;
        const rows = tableContainer.querySelectorAll('table tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 2) {
                const fileId = parseInt((cells[1].textContent || '').trim(), 10);
                if (!Number.isNaN(fileId)) {
                    row.setAttribute('data-id', fileId.toString());
                }
            }
        });
    }
    setupSortable() {
        const tableContainer = document.getElementById('overlay_file_group_sorter_table');
        if (!tableContainer)
            return;
        const tbody = tableContainer.querySelector('table tbody');
        if (!tbody)
            return;
        this.sortableTable = Sortable.create(tbody, {
            animation: 150,
            dataIdAttr: 'data-id'
        });
    }
    buildDesiredRanks() {
        this.desiredRanks.clear();
        if (!this.sortableTable)
            return;
        const order = this.sortableTable.toArray().map((id) => parseInt(id, 10));
        order.forEach((fileId, idx) => {
            if (!Number.isNaN(fileId)) {
                this.desiredRanks.set(fileId, idx + 1);
            }
        });
    }
    async handleSubmit() {
        if (!this.overlay)
            return;
        let capturedDebugOptions = this.overlay.getDebugOptions();
        if (!capturedDebugOptions) {
            capturedDebugOptions = { debug: false, log: false };
        }
        this.buildDesiredRanks();
        const desiredOrder = Array.from(this.desiredRanks.entries())
            .sort((a, b) => a[1] - b[1])
            .map(([fileId]) => fileId);
        if (desiredOrder.length === 0) {
            const currentMessages = this.overlay['state'].messages || [];
            this.overlay.setState({
                messages: [...currentMessages, { type: 'error', text: 'No files found to sort' }]
            });
            return { _autoFade: false };
        }
        let hasDebugData = false;
        const maxIterations = desiredOrder.length;
        let iterationCount = 0;
        while (true) {
            iterationCount++;
            if (iterationCount > maxIterations) {
                const currentMessages = this.overlay['state'].messages || [];
                this.overlay.setState({
                    messages: [...currentMessages, { type: 'error', text: `Sorting failed: exceeded maximum iterations (${maxIterations}).` }]
                });
                return { _autoFade: false };
            }
            let maxDistance = 0;
            let fileToMove = null;
            for (const [fileId, desiredRank] of this.desiredRanks.entries()) {
                const currentRank = this.currentRanks.get(fileId);
                if (currentRank === undefined)
                    continue;
                if (currentRank === desiredRank)
                    continue;
                const distance = Math.abs(currentRank - desiredRank);
                if (distance > maxDistance) {
                    maxDistance = distance;
                    fileToMove = { fileId, desiredRank, distance };
                }
            }
            if (!fileToMove || maxDistance === 0) {
                break;
            }
            try {
                const response = await this.rpc.call('set_file_rank', {
                    page_id: this.pageId,
                    file_id: fileToMove.fileId,
                    target_rank: fileToMove.desiredRank
                }, capturedDebugOptions);
                if (response?.debug?.entries?.length) {
                    hasDebugData = true;
                    handleRPCResponseWithDebug(response, 'set_file_rank', {
                        page_id: this.pageId,
                        file_id: fileToMove.fileId,
                        target_rank: fileToMove.desiredRank
                    });
                }
                const responseData = response.data;
                if (responseData?.files?.length) {
                    responseData.files.forEach(f => this.currentRanks.set(f.id, f.file_rank));
                }
                else {
                    // Fallback: update current rank for moved file only
                    this.currentRanks.set(fileToMove.fileId, fileToMove.desiredRank);
                }
                const currentMessages = this.overlay['state'].messages || [];
                this.overlay.setState({
                    messages: [...currentMessages, { type: 'success', text: `Moved file ${fileToMove.fileId} to rank ${fileToMove.desiredRank}` }]
                });
            }
            catch (error) {
                const currentMessages = this.overlay['state'].messages || [];
                const msg = error instanceof Error ? error.message : String(error);
                this.overlay.setState({
                    messages: [...currentMessages, { type: 'error', text: `Failed to move file ${fileToMove.fileId}: ${msg}` }]
                });
                if (error && error.debug?.entries?.length) {
                    handleRPCResponseWithDebug(error, 'set_file_rank', {
                        page_id: this.pageId,
                        file_id: fileToMove.fileId,
                        target_rank: fileToMove.desiredRank
                    });
                    hasDebugData = true;
                }
            }
        }
        return {
            _showMessage: 'File order updated',
            _autoFade: !hasDebugData,
            _redirectAfterFade: hasDebugData ? null : 'self'
        };
    }
}
