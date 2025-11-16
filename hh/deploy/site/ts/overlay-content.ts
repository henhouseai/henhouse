/**
 * OverlayContent - Container for pluggable content components.
 */

export interface OverlayContentProps {
  children?: string | HTMLElement | Array<string | HTMLElement>;
  headers?: Array<string>; // Optional array of header strings for each content section
  className?: string;
}

export class OverlayContent {
  private props: OverlayContentProps;

  constructor(props: OverlayContentProps) {
    this.props = props;
  }

  /**
   * Render the content element.
   */
  render(): HTMLElement {
    // If children is an array, handle paired headers and content
    if (Array.isArray(this.props.children)) {
      const container = document.createElement('div');
      const headers = this.props.headers || [];
      const contentItems = this.props.children;
      
      // Determine max length to iterate through both arrays
      const maxLength = Math.max(headers.length, contentItems.length);
      
      for (let i = 0; i < maxLength; i++) {
        const headerText = headers[i];
        const contentItem = contentItems[i];
        
        // Skip if no content item
        if (!contentItem) continue;
        
        // Create header if header text exists and is not blank
        if (headerText !== undefined && headerText !== '') {
          const headerDiv = document.createElement('div');
          headerDiv.className = 'overlayContentHeader';
          
          // Create expand/collapse button
          const toggleBtn = document.createElement('button');
          toggleBtn.className = 'overlay-content-toggle';
          toggleBtn.textContent = '▼'; // Expanded state (down arrow)
          toggleBtn.type = 'button';
          
          // Create header text span
          const headerTextSpan = document.createElement('span');
          headerTextSpan.className = 'overlay-content-header-text';
          headerTextSpan.textContent = headerText;
          
          headerDiv.appendChild(toggleBtn);
          headerDiv.appendChild(headerTextSpan);
          
          // Create content div
          const contentDiv = document.createElement('div');
          contentDiv.className = 'overlayContent';
          
          if (this.props.className) {
            contentDiv.className += ` ${this.props.className}`;
          }
          
          if (typeof contentItem === 'string') {
            contentDiv.innerHTML = contentItem;
          } else {
            contentDiv.appendChild(contentItem);
          }
          
          // Set initial collapsed state based on header text
          // Request: expanded, Response: collapsed
          const isCollapsed = headerText.toLowerCase() === 'response';
          if (isCollapsed) {
            contentDiv.style.display = 'none';
            toggleBtn.textContent = '▶'; // Collapsed state (right arrow)
          }
          
          // Add click handler for expand/collapse
          toggleBtn.addEventListener('click', () => {
            const isCurrentlyCollapsed = contentDiv.style.display === 'none';
            if (isCurrentlyCollapsed) {
              contentDiv.style.display = '';
              toggleBtn.textContent = '▼';
            } else {
              contentDiv.style.display = 'none';
              toggleBtn.textContent = '▶';
            }
          });
          
          container.appendChild(headerDiv);
          container.appendChild(contentDiv);
        } else {
          // No header - just create content div
          const contentDiv = document.createElement('div');
          contentDiv.className = 'overlayContent';
          
          if (this.props.className) {
            contentDiv.className += ` ${this.props.className}`;
          }
          
          if (typeof contentItem === 'string') {
            contentDiv.innerHTML = contentItem;
          } else {
            contentDiv.appendChild(contentItem);
          }
          
          container.appendChild(contentDiv);
        }
      }
      
      return container;
    }
    
    // Single child - wrap in overlayContent div (original behavior)
    const content = document.createElement('div');
    content.className = 'overlayContent';

    if (this.props.className) {
      content.className += ` ${this.props.className}`;
    }

    // Handle children
    if (this.props.children) {
      if (typeof this.props.children === 'string') {
        content.innerHTML = this.props.children;
      } else {
        content.appendChild(this.props.children);
      }
    }

    return content;
  }
}

