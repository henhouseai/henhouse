# Modify Text Enhancement Analysis

## Overview

This document analyzes the current `modify_text` functionality in Henhouse and proposes enhancements to support more flexible text editing operations beyond complete content replacement.

## Current modify_text Implementation

### Core Functionality

The `modify_text` method currently provides a complete content replacement system:

```python
def modify_text(self, text: str) -> bool:
    # 1. Validate new text through TextProcessor.preprocess()
    # 2. Update database with complete replacement
    # 3. Refresh links table
    # 4. Invalidate caches
    # 5. Return success/failure
```

### Action Interface

```python
@register_action('modify_text')
def modify_text() -> bool:
    # Parameters: page_id, text (complete replacement)
    # Returns: Full page data with updated content
```

### Processing Pipeline

1. **Input Validation**: `page_id` and `text` parameters required
2. **Text Processing**: Full TextProcessor.preprocess() validation
3. **Database Update**: Complete text replacement in pages table
4. **Link Management**: Update links table with new page/image references
5. **Cache Management**: Invalidate prepared_text and related caches
6. **Response**: Return complete page data with processed content

### Current Limitations

1. **Complete Replacement Only**: Cannot prepend, append, or modify specific sections
2. **No Targeted Editing**: Cannot replace specific strings within content
3. **All-or-Nothing**: Any text change requires full revalidation and recaching

## Proposed Enhancements

### 1. Insert Mode (Prepend/Append)

Add support for inserting text at the beginning or end of existing content.

#### Use Cases
- Adding headers/footers to pages
- Accumulating content over time
- Template-based content assembly

#### Implementation
```python
modify_text(page_id=123, text="new content", mode="prepend")
modify_text(page_id=123, text="new content", mode="append")
```

### 2. Targeted Replace Mode

Add support for find-and-replace operations with exact string matching.

#### Requirements
- **Exactly 1 match required**: Fail if target string appears 0 or multiple times
- **Case-sensitive matching**: Preserve exact string matching behavior
- **Full validation**: Combined result must pass TextProcessor validation

#### Use Cases
- Updating specific links or references
- Correcting typos in specific locations
- Targeted content updates without full replacement

#### Implementation
```python
modify_text(page_id=123, text="new value", mode="replace",
           old_string="unique target string")
```

## Design Decision: Extend vs Separate Tools

### Option Analysis

#### Extend Existing modify_text
**Pros:**
- Unified validation pipeline (all text changes through TextProcessor)
- Consistent caching and link management
- Single API endpoint to maintain
- Backwards compatible
- Progressive enhancement possible

**Cons:**
- Parameter complexity increases
- Mode-specific validation logic
- Single tool becomes multi-purpose

#### Separate Tools
**Pros:**
- Clear separation of concerns
- Simpler individual implementations
- Focused error handling per operation type

**Cons:**
- Code duplication (validation, caching, links)
- Multiple API endpoints
- Inconsistent behavior risk
- Harder to maintain

### Recommendation: Extend Existing Tool

**Rationale:**
- Text editing inherently requires the same validation, caching, and link management infrastructure
- Unifying under one tool ensures consistency across all text modifications
- Backwards compatibility maintains existing integrations
- Single tool is easier to document and test

## Implementation Details

### Parameter Design

```python
def modify_text(page_id: int, text: str, mode: str = "replace_all",
               old_string: str = None) -> bool:
    """
    Modify page text with flexible editing modes.

    Args:
        page_id: Target page identifier
        text: New text content (interpretation depends on mode)
        mode: Editing mode
            - "replace_all": Complete replacement (current behavior)
            - "prepend": Insert text at beginning
            - "append": Insert text at end
            - "replace": Replace old_string with text (exactly 1 match required)
        old_string: Target string for replace mode (required when mode="replace")
    """
```

### Mode-Specific Logic

#### replace_all Mode (Current Behavior)
```python
new_content = text
# Full TextProcessor validation
```

#### prepend/append Modes
```python
current_content = self.text or ""
if mode == "prepend":
    new_content = text + current_content
else:  # append
    new_content = current_content + text
# Full TextProcessor validation of combined content
```

#### replace Mode
```python
current_content = self.text or ""
if not old_string:
    raise ValueError("old_string required for replace mode")

match_count = current_content.count(old_string)
if match_count == 0:
    raise ValueError(f"old_string '{old_string}' not found in content")
elif match_count > 1:
    raise ValueError(f"old_string '{old_string}' appears {match_count} times - must be unique")

new_content = current_content.replace(old_string, text, 1)
# Full TextProcessor validation of result
```

### Validation and Safety

#### TextProcessor Integration
- All modes validate final combined content through `TextProcessor.preprocess()`
- Link validation and parsing remains consistent
- Markup syntax validation applies to all modifications

#### Error Handling
- Invalid markup syntax: Fail with parse error details
- Missing old_string in replace mode: Parameter validation error
- Multiple matches in replace mode: Uniqueness violation error
- Database update failures: Rollback and error reporting

#### Transaction Safety
- Database updates remain atomic
- Links table updates maintain referential integrity
- Cache invalidation handles partial failures

### Caching Considerations

#### Cache Invalidation
- All modes trigger `prepared_text` cache invalidation
- Links table cache refresh required for all modes
- Page modification flagging consistent across modes

#### Performance Impact
- Prepend/append: Minimal overhead (string concatenation)
- Replace: String operations + validation
- All modes: Same TextProcessor validation cost

### Migration Strategy

#### Phase 1: Core Infrastructure
- Add mode parameter to existing action
- Implement prepend/append modes
- Maintain backwards compatibility

#### Phase 2: Advanced Features
- Add replace mode with uniqueness validation
- Enhanced error reporting for match failures
- Performance optimizations

#### Phase 3: Extended Capabilities
- Consider regex support for replace mode
- Multiple match handling options
- Undo/redo capabilities

## API Design Considerations

### Command Line Interface
```bash
# Current usage (unchanged)
hen modify-text -page_id 123 -text "new content"

# New modes
hen modify-text -page_id 123 -text "prefix" -mode prepend
hen modify-text -page_id 123 -text "new value" -mode replace -old_string "old value"
```

### MCP Interface
```json
{
  "method": "tools/call",
  "params": {
    "name": "modify_text",
    "arguments": {
      "page_id": 123,
      "text": "new content",
      "mode": "prepend"
    }
  }
}
```

### HTTP Interface
```javascript
// Existing
fetch('/modify_text', {
  method: 'POST',
  body: JSON.stringify({ page_id: 123, text: "new content" })
});

// Enhanced
fetch('/modify_text', {
  method: 'POST',
  body: JSON.stringify({
    page_id: 123,
    text: "new value",
    mode: "replace",
    old_string: "old value"
  })
});
```

## Testing Strategy

### Unit Tests
- Mode-specific validation logic
- TextProcessor integration verification
- Cache invalidation testing
- Error condition handling

### Integration Tests
- Full modify_text action flow
- Database transaction integrity
- Link table updates
- Cache consistency

### Edge Cases
- Empty current content
- Empty new content
- Unicode characters
- Very large content
- Concurrent modifications

## Future Extensions

### Advanced Replace Options
- Regex pattern matching
- Case-insensitive matching
- Multiple match handling (first N, all)
- Contextual replacement (within specific sections)

### Collaborative Editing
- Change tracking and conflict resolution
- Multi-user edit merging
- Version history integration

### Content Templates
- Template-based insertions
- Variable substitution
- Conditional content blocks

## Conclusion

Extending the existing `modify_text` tool with mode-based editing provides the best balance of functionality, maintainability, and backwards compatibility. The unified validation and caching pipeline ensures consistency while enabling powerful new editing capabilities.

The proposed implementation maintains the robustness of the current system while adding flexibility for common text editing scenarios, particularly useful for agent-driven content management and incremental content updates.