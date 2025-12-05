/**
 * Overlay Link Helpers - Utilities for intercepting and modifying links in overlay content.
 * Provides standardized functions for:
 * - Converting page/image links to JavaScript handlers
 * - Modifying element IDs (adding prefixes)
 * - Scanning and processing links in containers
 */
/**
 * Intercept links in a container according to the provided options.
 * @param container - Container element to scan for links
 * @param options - Interception options
 */
export function interceptLinks(container, options = {}) {
    const { onPageLink, onImageLink, onFileLink, skipSelector = 'a[class*="updatePageView_"]', customMatcher, customHandler, markerProperty = '__overlayIntercepted' } = options;
    // Find all links (with or without href - some links use IDs instead)
    const links = container.querySelectorAll('a');
    links.forEach(link => {
        // Skip links that match the skip selector
        if (skipSelector && link.matches(skipSelector)) {
            return;
        }
        // Skip links that already have our marker (avoid duplicate listeners)
        if (link[markerProperty]) {
            return;
        }
        const href = link.getAttribute('href') || '';
        // Try custom matcher first (works even without href - can match on ID, class, etc.)
        if (customMatcher && customMatcher(href, link)) {
            if (customHandler) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    customHandler(href, link);
                });
                link[markerProperty] = true;
            }
            return;
        }
        // Skip links without href for standard matchers (unless custom matcher handled it)
        if (!href) {
            return;
        }
        // Check if it's a page link (starts with / and is numeric)
        const pageMatch = href.match(/^\/(\d+)$/);
        if (pageMatch && onPageLink) {
            const pageId = parseInt(pageMatch[1], 10);
            link.addEventListener('click', (e) => {
                e.preventDefault();
                onPageLink(pageId, link);
            });
            link[markerProperty] = true;
            return;
        }
        // Check if it's an image link (starts with /img/)
        const imageMatch = href.match(/^\/img\/(\d+)$/);
        if (imageMatch && onImageLink) {
            const imageId = parseInt(imageMatch[1], 10);
            link.addEventListener('click', (e) => {
                e.preventDefault();
                onImageLink(imageId, link);
            });
            link[markerProperty] = true;
            return;
        }
        // Check if it's a file link (starts with /file/)
        const fileMatch = href.match(/^\/file\/(\d+)$/);
        if (fileMatch && onFileLink) {
            const fileId = parseInt(fileMatch[1], 10);
            link.addEventListener('click', (e) => {
                e.preventDefault();
                onFileLink(fileId, link);
            });
            link[markerProperty] = true;
            return;
        }
    });
}
/**
 * Add a prefix to all element IDs in a container.
 * Useful for adding "overlay_" prefix to IDs in overlay content.
 * @param container - Container element to scan for IDs
 * @param prefix - Prefix to add (e.g., "overlay_")
 */
export function addIdPrefix(container, prefix) {
    // Find all elements with IDs
    const elementsWithIds = container.querySelectorAll('[id]');
    elementsWithIds.forEach(element => {
        const currentId = element.getAttribute('id');
        if (currentId && !currentId.startsWith(prefix)) {
            element.setAttribute('id', prefix + currentId);
        }
    });
}
/**
 * Remove a prefix from all element IDs in a container.
 * @param container - Container element to scan for IDs
 * @param prefix - Prefix to remove (e.g., "overlay_")
 */
export function removeIdPrefix(container, prefix) {
    // Find all elements with IDs
    const elementsWithIds = container.querySelectorAll('[id]');
    elementsWithIds.forEach(element => {
        const currentId = element.getAttribute('id');
        if (currentId && currentId.startsWith(prefix)) {
            element.setAttribute('id', currentId.substring(prefix.length));
        }
    });
}
