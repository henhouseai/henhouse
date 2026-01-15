/**
 * document_page_data - Handles document pages.
 * Metadata fields (output_filename, output_format) are automatically discovered by base class.
 * For now, simple extension with no custom handlers.
 */

import { PageData, GetPageResponse, FieldMapping } from '../../../../../hh/deploy/site/ts/page-data.js';
import { PageManager } from '../../../../../hh/deploy/site/ts/page-manager.js';
import { OverlayManager } from '../../../../../hh/deploy/site/ts/overlay/overlay-manager.js';

export class document_page_data extends PageData {
  constructor(data: GetPageResponse) {
    super(data);
  }

  /**
   * Override to provide field mappings for document specific fields
   */
  protected getFieldMappings(): FieldMapping[] {
    return [
      ...super.getFieldMappings(), // Include base page mappings (name, text)
      // Document specific mappings
      {
        fields: ['output_filename'],
        apiTool: 'modify_document_info',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          output_filename: values['output_filename']
        })
      },
      {
        fields: ['output_format'],
        apiTool: 'modify_document_info',
        priority: 0,
        buildParams: (fields, values, pageId) => ({
          page_id: pageId,
          output_format: values['output_format']
        })
      }
    ];
  }

  /**
   * Handler for document_combo: Edit output_filename and output_format
   */
  async document_combo(rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const pageManager = PageManager.getInstance();

      // Get editable fields
      const currentOutputFilename = this.getField('output_filename', 'form') || '';
      const currentOutputFormat = this.getField('output_format', 'form') || '';

      // Get read-only fields
      const pageIdValue = this.getField('id') || '';
      const pageClass = this.getField('class') || '';
      const pageLink = this.getField('link') || '';
      const lastModified = this.getField('last_modified') || '';
      const username = this.getField('username') || '';
      const path = this.getField('path') || [];
      const pathStr = Array.isArray(path) ? path.map((p: any) => p.name).filter(Boolean).join(' / ') : '';

      // Create form HTML with editable and read-only fields
      const editableFieldsHtml = `
          <div class="overlay-form-group">
            <label>Output Filename:</label>
            <input type="text" id="page-field-output_filename" value="${this.escapeHtml(currentOutputFilename)}" class="overlay-form-input">
          </div>
          <div class="overlay-form-group">
            <label>Output Format:</label>
            <select id="page-field-output_format" class="overlay-form-input">
              <option value="markdown" ${currentOutputFormat === 'markdown' ? 'selected' : ''}>Markdown</option>
              <option value="html" ${currentOutputFormat === 'html' ? 'selected' : ''}>HTML</option>
              <option value="json" ${currentOutputFormat === 'json' ? 'selected' : ''}>JSON</option>
            </select>
          </div>
      `;

      const readOnlyFieldsHtml = `
          <div class="overlay-form-grid">
            <div><strong>ID:</strong></div>
            <div>${this.escapeHtml(String(pageIdValue))}</div>
            <div><strong>Class:</strong></div>
            <div>${this.escapeHtml(pageClass)}</div>
            <div><strong>Link:</strong></div>
            <div>${this.escapeHtml(pageLink)}</div>
            <div><strong>Last Modified:</strong></div>
            <div>${this.escapeHtml(lastModified)}</div>
            <div><strong>Username:</strong></div>
            <div>${this.escapeHtml(username)}</div>
            <div><strong>Path:</strong></div>
            <div>${this.escapeHtml(pathStr)}</div>
          </div>
      `;

      OverlayManager.getInstance().show({
        header: 'Edit Document',
        content: [editableFieldsHtml, readOnlyFieldsHtml],
        contentHeaders: ['Editable Fields', 'Read-Only Fields (for display only)'],
        mode: 'fixed',
        closable: true,
        submitLabel: 'Submit',
        cancelLabel: 'Cancel',
        onCancel: () => {
          pageManager.clearFieldRegistry();
        },
        onUnmount: () => {
          pageManager.clearFieldRegistry();
        },
        onSubmit: async () => {
          // Process operations incrementally
          const changedFields = pageManager['detectChangedFields']();
          const editableFields = changedFields.filter((field: string) => field !== 'class');

          if (editableFields.length === 0) {
            return { success: true, noChanges: true, _showMessage: 'No changes made', _autoFade: true };
          }

          const optimalMappings = pageManager['selectOptimalMappings'](editableFields);
          const currentValues = pageManager['extractFormValues']();

          if (!pageId) {
            throw new Error('No page ID available');
          }

          const result = await this.processOperationsIncrementally(rpc, optimalMappings, currentValues, pageId);
          const allSucceeded = result.success && result.errors.length === 0;

          if (allSucceeded) {
            // Update output_filename and output_format in internal PageData if they were changed
            const outputFilenameOp = result.operations?.find((op: any) => op.fields?.includes('output_filename'));
            if (outputFilenameOp && outputFilenameOp.success && outputFilenameOp.result) {
              const parsedResult = rpc.extractAPIData(outputFilenameOp.result);
              const resultPageData = parsedResult?.page || parsedResult;
              const newOutputFilename = resultPageData?.output_filename;
              if (newOutputFilename !== undefined) {
                this.updateFieldValue('output_filename', newOutputFilename);
              }
            }

            const outputFormatOp = result.operations?.find((op: any) => op.fields?.includes('output_format'));
            if (outputFormatOp && outputFormatOp.success && outputFormatOp.result) {
              const parsedResult = rpc.extractAPIData(outputFormatOp.result);
              const resultPageData = parsedResult?.page || parsedResult;
              const newOutputFormat = resultPageData?.output_format;
              if (newOutputFormat !== undefined) {
                this.updateFieldValue('output_format', newOutputFormat);
              }
            }

            return { ...result, _autoFade: true };
          } else {
            // Don't throw - errors are already shown in overlay
            return { ...result };
          }
        }
      });

      // Focus the output filename input after overlay is shown
      setTimeout(() => {
        const input = document.getElementById('page-field-output_filename') as HTMLInputElement;
        if (input) {
          input.focus();
          input.select();
        }
      }, 100);
    } catch (error) {
      rpc.showError('document_combo', error);
    }
  }
}