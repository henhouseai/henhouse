/**
 * PageActionsImages - Mixin for image management actions (copy_images_app, move_images_app, delete_images_app)
 */

import type { PageData } from './page-data.js';

export class PageActionsImages {
  /**
   * Handler for copy_images_app: Copy images to current page
   */
  async copy_images_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'image',
        initialPageId: pageId,
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'imageIds' in result) {
            const imageResult = result as { imageIds: number[]; imageInstances: Array<{ image_id: number; source_page_id: number; source_rank: number }> };
            
            // Get browser overlay to add messages incrementally and capture debug options
            const browserOverlay = (browser as any).overlay;
            
            // Capture debug options from the browser overlay (where user sets them)
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            // If no debug options in browser overlay, use empty object
            if (!capturedDebugOptions) {
              capturedDebugOptions = { debug: false, log: false };
            }
            
            // Track if any debug data was present
            let hasDebugData = false;
            
            // Process each image individually to show incremental success messages
            for (const imageId of imageResult.imageIds) {
              try {
                // Call copy_image action for each image
                const response = await rpc.call('copy_image', {
                  target_page: pageId,
                  image_id: imageId
                }, capturedDebugOptions);
                
                // Handle debug data if present
                if (response && response.debug && Array.isArray(response.debug.entries) && response.debug.entries.length > 0) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'copy_image', {
                    target_page: pageId,
                    image_id: imageId
                  });
                }
                
                if (response && response.data) {
                  // Add success message for this image
                  if (browserOverlay) {
                    const currentMessages = (browserOverlay as any)['state'].messages || [];
                    browserOverlay.setState({
                      messages: [...currentMessages, { type: 'success' as const, text: `Successfully copied image ${imageId}` }]
                    });
                  }
                }
              } catch (error) {
                // Add error message for this image
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const errorMsg = error instanceof Error ? error.message : String(error);
                  
                  // Check if it's an RPCError with multiple errors
                  const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray((error as any).errors))
                    ? (error as any).errors
                    : [];
                  
                  // Add main error message
                  const newMessages = [{ type: 'error' as const, text: `Failed to copy image ${imageId}: ${errorMsg}` }];
                  
                  // Add detailed errors if available
                  if (detailedErrors.length > 0) {
                    detailedErrors.forEach((err: { type?: string; content: string }) => {
                      newMessages.push({
                        type: 'error' as const,
                        text: `${err.type || 'error'}: ${err.content}`
                      });
                    });
                  }
                  
                  browserOverlay.setState({
                    messages: [...currentMessages, ...newMessages]
                  });
                  
                  // Handle debug data if present
                  if (error && typeof error === 'object' && 'debug' in error) {
                    const errorDebug = (error as any).debug;
                    if (errorDebug && Array.isArray(errorDebug.entries) && errorDebug.entries.length > 0) {
                      const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                      handleRPCResponseWithDebug(error, 'copy_image', {
                        target_page: pageId,
                        image_id: imageId
                      });
                    }
                  }
                }
              }
            }
            
            // Return success with redirect flag (reload page after fade, unless debug data present)
            return {
              _showMessage: `Completed copying ${imageResult.imageIds.length} image(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('copy_images_app', error);
    }
  }

  /**
   * Handler for move_images_app: Move images to current page
   */
  async move_images_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'image',
        initialPageId: pageId,
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'imageInstances' in result) {
            const imageResult = result as { imageIds: number[]; imageInstances: Array<{ image_id: number; source_page_id: number; source_rank: number }> };
            
            // Get browser overlay to add messages incrementally and capture debug options
            const browserOverlay = (browser as any).overlay;
            
            // Capture debug options from the browser overlay (where user sets them)
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            // If no debug options in browser overlay, use empty object
            if (!capturedDebugOptions) {
              capturedDebugOptions = { debug: false, log: false };
            }
            
            // Group image instances by source page
            const instancesBySourcePage: { [key: number]: Array<{ image_id: number; source_rank: number }> } = {};
            imageResult.imageInstances.forEach((instance: { image_id: number; source_page_id: number; source_rank: number }) => {
              if (!instancesBySourcePage[instance.source_page_id]) {
                instancesBySourcePage[instance.source_page_id] = [];
              }
              instancesBySourcePage[instance.source_page_id].push({ image_id: instance.image_id, source_rank: instance.source_rank });
            });
            
            // Track if any debug data was present
            let hasDebugData = false;
            
            // Process each source page group
            for (const [sourcePageId, instances] of Object.entries(instancesBySourcePage)) {
              const sourceRanks = instances.map(inst => inst.source_rank).join(',');
              const params = {
                source_page: parseInt(sourcePageId, 10),
                target_page: pageId,
                source_rank: sourceRanks
              };
              
              try {
                // Call move_images action with captured debug options
                const response = await rpc.call('move_images', params, capturedDebugOptions);
                
                // Handle debug data if present
                if (response && response.debug && Array.isArray(response.debug.entries) && response.debug.entries.length > 0) {
                  hasDebugData = true;
                  const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                  handleRPCResponseWithDebug(response, 'move_images', params);
                }
                
                if (response && response.data) {
                  // Add success message for this group of images
                  const imageIds = instances.map(inst => inst.image_id).join(', ');
                  if (browserOverlay) {
                    const currentMessages = (browserOverlay as any)['state'].messages || [];
                    browserOverlay.setState({
                      messages: [...currentMessages, { type: 'success' as const, text: `Successfully moved image(s) ${imageIds} from page ${sourcePageId}` }]
                    });
                  }
                } else {
                  throw new Error(`Failed to move images from page ${sourcePageId}`);
                }
              } catch (error) {
                // Add error message for this group
                if (browserOverlay) {
                  const currentMessages = (browserOverlay as any)['state'].messages || [];
                  const errorMsg = error instanceof Error ? error.message : String(error);
                  
                  // Check if it's an RPCError with multiple errors
                  const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray((error as any).errors))
                    ? (error as any).errors
                    : [];
                  
                  // Add main error message
                  const newMessages = [{ type: 'error' as const, text: `Failed to move images from page ${sourcePageId}: ${errorMsg}` }];
                  
                  // Add detailed errors if available
                  if (detailedErrors.length > 0) {
                    detailedErrors.forEach((err: { type?: string; content: string }) => {
                      newMessages.push({
                        type: 'error' as const,
                        text: `${err.type || 'error'}: ${err.content}`
                      });
                    });
                  }
                  
                  browserOverlay.setState({
                    messages: [...currentMessages, ...newMessages]
                  });
                  
                  // Handle debug data if present
                  if (error && typeof error === 'object' && 'debug' in error) {
                    const errorDebug = (error as any).debug;
                    if (errorDebug && Array.isArray(errorDebug.entries) && errorDebug.entries.length > 0) {
                      const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                      handleRPCResponseWithDebug(error, 'move_images', params);
                    }
                  }
                }
              }
            }
            
            // Return success with redirect flag (reload page after fade, unless debug data present)
            const totalImages = imageResult.imageIds.length;
            return {
              _showMessage: `Completed moving ${totalImages} image(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('move_images_app', error);
    }
  }

  /**
   * Handler for delete_images_app: Delete images from their source pages
   */
  async delete_images_app(this: PageData, rpc: any): Promise<void> {
    const pageId = this.id;
    if (!pageId) {
      alert('No page ID found');
      return;
    }

    try {
      const { Browser } = await import('./browser.js');
      const browser = new Browser({
        mode: 'image',
        initialPageId: pageId,
        onSubmit: async (result: any) => {
          if (typeof result === 'object' && 'imageInstances' in result) {
            const imageResult = result as { imageIds: number[]; imageInstances: Array<{ image_id: number; source_page_id: number; source_rank: number }> };
            
            // Get browser overlay to add messages incrementally and capture debug options
            const browserOverlay = (browser as any).overlay;
            
            // Capture debug options from the browser overlay (where user sets them)
            let capturedDebugOptions = browserOverlay ? browserOverlay.getDebugOptions() : null;
            // If no debug options in browser overlay, use empty object
            if (!capturedDebugOptions) {
              capturedDebugOptions = { debug: false, log: false };
            }
            
            // Group image instances by source page
            const instancesBySourcePage: { [key: number]: Array<{ image_id: number; source_rank: number }> } = {};
            imageResult.imageInstances.forEach((instance: { image_id: number; source_page_id: number; source_rank: number }) => {
              if (!instancesBySourcePage[instance.source_page_id]) {
                instancesBySourcePage[instance.source_page_id] = [];
              }
              instancesBySourcePage[instance.source_page_id].push({ image_id: instance.image_id, source_rank: instance.source_rank });
            });
            
            // Track if any debug data was present
            let hasDebugData = false;
            
            // Process each source page group
            for (const [sourcePageId, instances] of Object.entries(instancesBySourcePage)) {
              // Sort instances by rank in reverse order (highest rank first) to avoid rank shifting issues
              const sortedInstances = [...instances].sort((a, b) => b.source_rank - a.source_rank);
              
              // Process each image instance for this page (in reverse rank order)
              for (const instance of sortedInstances) {
                // Define params outside try block so it's accessible in catch block
                const params = {
                  page_id: parseInt(sourcePageId, 10),
                  image_id: instance.image_id,
                  rank: instance.source_rank
                };
                
                try {
                  // Call remove_image action for each instance
                  const response = await rpc.call('remove_image', params, capturedDebugOptions);
                  
                  // Handle debug data if present
                  if (response && response.debug && Array.isArray(response.debug.entries) && response.debug.entries.length > 0) {
                    hasDebugData = true;
                    const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                    handleRPCResponseWithDebug(response, 'remove_image', params);
                  }
                  
                  if (response && response.data) {
                    // Add success message for this image instance
                    if (browserOverlay) {
                      const currentMessages = (browserOverlay as any)['state'].messages || [];
                      browserOverlay.setState({
                        messages: [...currentMessages, { type: 'success' as const, text: `Successfully removed image ${instance.image_id} (rank ${instance.source_rank}) from page ${sourcePageId}` }]
                      });
                    }
                  } else {
                    throw new Error(`Failed to remove image ${instance.image_id} from page ${sourcePageId}`);
                  }
                } catch (error) {
                  // Add error message for this image instance
                  if (browserOverlay) {
                    const currentMessages = (browserOverlay as any)['state'].messages || [];
                    const errorMsg = error instanceof Error ? error.message : String(error);
                    
                    // Check if it's an RPCError with multiple errors
                    const detailedErrors = (error && typeof error === 'object' && 'errors' in error && Array.isArray((error as any).errors))
                      ? (error as any).errors
                      : [];
                    
                    // Add main error message
                    const newMessages = [{ type: 'error' as const, text: `Failed to remove image ${instance.image_id} (rank ${instance.source_rank}) from page ${sourcePageId}: ${errorMsg}` }];
                    
                    // Add detailed errors if available
                    if (detailedErrors.length > 0) {
                      detailedErrors.forEach((err: { type?: string; content: string }) => {
                        newMessages.push({
                          type: 'error' as const,
                          text: `${err.type || 'error'}: ${err.content}`
                        });
                      });
                    }
                    
                    browserOverlay.setState({
                      messages: [...currentMessages, ...newMessages]
                    });
                    
                    // Handle debug data if present
                    if (error && typeof error === 'object' && 'debug' in error) {
                      const errorDebug = (error as any).debug;
                      if (errorDebug && Array.isArray(errorDebug.entries) && errorDebug.entries.length > 0) {
                        const { handleRPCResponseWithDebug } = await import('./debug-helper.js');
                        handleRPCResponseWithDebug(error, 'remove_image', params);
                      }
                    }
                  }
                }
              }
            }
            
            // Return success with redirect flag (reload page after fade, unless debug data present)
            const totalImages = imageResult.imageIds.length;
            return {
              _showMessage: `Completed removing ${totalImages} image instance(s)`,
              _autoFade: !hasDebugData,
              _redirectAfterFade: hasDebugData ? null : 'self'
            };
          }
        }
      });
      await browser.show();
    } catch (error) {
      rpc.showError('delete_images_app', error);
    }
  }
}

