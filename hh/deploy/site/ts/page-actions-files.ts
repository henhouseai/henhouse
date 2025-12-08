/**
 * PageActionsFiles - Mixin for file management actions (upload_files_app for now)
 */

import { getSeedData } from './seed.js';

export class PageActionsFiles {
  /**
   * Handler for upload_files_app: Upload files to current page
   */
  async upload_files_app(rpc: any): Promise<void> {
    const pageId = (this as any).id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    const { UploadHandler } = await import('./upload-handler.js');
    const handler = new UploadHandler(rpc, getSeedData(), 'file');
    await handler.handle();
  }
}


