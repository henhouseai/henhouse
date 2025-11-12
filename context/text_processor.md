# TextProcessor System

A text processing system that transforms structured markup into formatted output through a decorator-based pipeline architecture.

## Overview

TextProcessor transforms structured markup into output formats using a decorator pipeline pattern. Text flows through a series of transformation functions for formatting, translation, and output generation.

## Core Architecture

### Pipeline Processing Model

TextProcessor uses a **pipeline architecture** where text flows through decorators in a specific order:

```
Input Text → First Decorator → User Decorators → Final Decorator → Output
```

Each decorator is a pure function that receives text input and returns transformed text output.

### Format-Agnostic Design

The system generates different output formats by changing the final decorator:

```python
# JSON output (default)
parser = TextProcessor(final_decorator='mcp')

# CLI table output  
parser = TextProcessor(final_decorator='parser')

# Same input, different outputs:
# Input: [[home page]]
# JSON: {"type": "page_link", "resolved_page": {"id": 1, "name": "home page"}}
# Parser: Formatted CLI table with page link information
```

## Syntax Reference

### Basic Elements

#### Text Links
- `[[123456]]` - Link to page ID 123456
- `[[link name]]` - Link to page with name "link name"
- `[[link name][display text]]` - Link with custom display text

#### Images
- `{{123456}}` - Primary image of page ID 123456
- `{{link name}}` - Primary image of page "link name"
- `{{link name}{caption text}}` - Image with custom caption
- `{{{7890}}}` - Direct image ID 7890
- `{{{7890}}{caption text}}` - Direct image with custom caption

#### Image-Links
- `[[123456][{{}}]]` - Image-link to page 123456 using its primary image
- `[[link name][{{other name}}]]` - Image-link using different page's image
- `[[link name][{{{7890}}{caption}}]]` - Image-link with specific image and caption

### Decorator Syntax

#### Basic Decorators
- `@decorator_name` - Apply decorator with no arguments
- `@decorator_name(arg1, arg2)` - Apply decorator with arguments
- `@decorator1 @decorator2 @decorator3` - Chain multiple decorators

#### Decorator Chaining
Decorators process **left-to-right** as a pipeline:
```
@hero @center @border {{link name}}
```
Becomes: `border(center(hero(base_text)))`

#### Pure Decorators
Decorators can be used without base elements:
- `@pi(5)` - Returns `{"type": "custom", "value": "3.14159"}`
- `@echo('Hello, World!')` - Returns `{"type": "custom", "value": "Hello, World!"}`
- `@mcp @pi(5)` - Returns JSON string `"{"type": "custom", "value": "3.14159"}"`

## Built-in Decorators

### Pure Decorators (No Base Element Required)
- **`@pi(precision)`** - Returns π with specified decimal places
  - `@pi(5)` → `{"type": "custom", "value": "3.14159"}`
  - `@pi(2)` → `{"type": "custom", "value": "3.14"}`

- **`@echo(text)`** - Returns the provided text
  - `@echo('Hello')` → `{"type": "custom", "value": "Hello"}`

### Transformation Decorators
- **`@repeat(count, separator)`** - Repeats text with optional separator
  - `@repeat(3, ', ')` on custom value → repeats it 3 times with separator

- **`@precision(decimals)`** - Formats decimal numbers
  - `@precision(2)` on numeric value → formats to 2 decimal places

### Final Output Decorators
- **`@mcp`** - Converts internal structure to JSON string (default final decorator)
- **`@parser`** - Converts internal structure to CLI table format

Note: Most decorators work with internal JSON structures (`{"type": "...", "value": "..."}`) and pass them through the pipeline. Final decorators (`@mcp`, `@parser`) convert these structures to string output.

## Technical Implementation

### Core Classes

#### TextProcessor
Main processing class:

```python
class TextProcessor:
    def __init__(self, first_decorator=None, final_decorator=None):
        # Initialize with optional global decorators
        
    def process(self, content: str) -> str:
        # Main processing method
        
    def update_links_table(self, conn, page_id: int) -> bool:
        # Database integration for link management
```

#### Decorator Registry
Manages decorator discovery and loading:

```python
@register_tp_decorator('decorator_name')
def my_decorator(text, **kwargs):
    """Custom decorator function"""
    return transformed_text
```

### Parsing Architecture

#### Recursive-Descent Parser
Handles:

- **Decorator parsing** with argument extraction
- **Nested element parsing** (links within images, etc.)
- **Whitespace handling** for decorator chaining
- **Error recovery** with detailed error reporting

#### Grammar Structure
```
UnparsedText = [Text] (DecoratedElement) [UnparsedText]
DecoratedElement = DecoratorChain BaseElement
DecoratorChain = DecoratorToken*
DecoratorToken = '@' DecoratorName ['(' Arguments ')'] Whitespace
BaseElement = LinkSyntax | ImageSyntax | NestedElement
```

### Database Integration

#### Links Table Management
Updates database tables with parsed link information:

- **`links` table** - Stores page-to-page references
- **`imageLinks` table** - Stores page-to-image references
- **Automatic cleanup** - Removes old links before adding new ones

#### Page Resolution
- **Page ID lookup** - Direct database queries by ID
- **Page name lookup** - Resolves page names to IDs
- **Error handling** - Graceful handling of missing pages/images

### Performance Features

#### Caching System
- JSON-based caching for decorator discovery
- Lazy loading of decorator functions
- Module validation for cached decorators
- Hot/cold cache management

#### Error Handling
- Parse error collection with detailed messages
- Database error handling for resolution failures
- Decorator error handling with graceful fallbacks
- Logging at all processing levels

## Usage Examples

### Basic Text Processing
```python
from hh.tp.tp import TextProcessor

# Simple processing (defaults to JSON output)
processor = TextProcessor()
result = processor.process("Hello [[world]]!")
# Output: JSON string with text and page link data

# CLI table output
parser_processor = TextProcessor(final_decorator='parser')
result = parser_processor.process("Check out [[home page]]")
# Output: Formatted CLI table showing the page link

# Pure decorator example
result = processor.process("@pi(5)")
# Output: {"type": "custom", "value": "3.14159"}
```

### Format-Specific Processing
```python
# JSON output (default)
json_processor = TextProcessor()  # or final_decorator='mcp'
json_result = json_processor.process("{{main page}}")
# Returns JSON structure

# CLI table output
parser_processor = TextProcessor(final_decorator='parser')
parser_result = parser_processor.process("{{main page}}")
# Returns formatted table with image info
```

### Database Integration
```python
import pymysql

# Process content and update database
processor = TextProcessor()
result = processor.process("Check out [[feature page]] and {{gallery}}")

# Update links table
conn = pymysql.connect(...)
processor.update_links_table(conn, page_id=123)
```

### Custom Decorators
```python
from hh.tp.tp_decorator_registry import register_tp_decorator

@register_tp_decorator('uppercase')
def uppercase_decorator(text, **kwargs):
    """Convert custom value to uppercase"""
    if isinstance(text, dict) and text.get('type') == 'custom':
        value = text.get('value', '')
        return {
            "type": "custom",
            "value": str(value).upper()
        }
    return text

@register_tp_decorator('multiply')
def multiply_decorator(text, **kwargs):
    """Multiply numeric custom value"""
    factor = kwargs.get('arg0', 2)
    if isinstance(text, dict) and text.get('type') == 'custom':
        try:
            value = float(text['value'])
            return {
                "type": "custom",
                "value": str(value * float(factor))
            }
        except:
            return text
    return text

# Usage
processor = TextProcessor()
result = processor.process("@uppercase @echo('hello')")
# Output: {"type": "custom", "value": "HELLO"}
```

## Advanced Features

### Decorator Argument Parsing
Decorators receive arguments as `arg0`, `arg1`, `arg2`, etc. in `kwargs`:

```python
# String arguments
@echo('Hello, World!')  # kwargs['arg0'] = 'Hello, World!'

# Numeric arguments  
@pi(5)  # kwargs['arg0'] = 5

# Multiple arguments
@repeat(3, ', ')  # kwargs['arg0'] = 3, kwargs['arg1'] = ', '

# Accessing in decorator function
def my_decorator(text, **kwargs):
    first_arg = kwargs.get('arg0')
    second_arg = kwargs.get('arg1')
    # ...
```

### Nested Element Support
Supports nested structures:

```python
# Image-links with custom captions
[[main page][{{gallery}{Custom Gallery Caption}}]]

# Multiple levels of nesting
@hero @center [[feature][{{banner}{Feature Banner}}]]
```

### Error Recovery
Provides error handling:

- Parse errors are collected and reported
- Database errors are logged with context
- Decorator errors fall back to original text
- Missing pages/images are handled gracefully

## Integration Points

### Henhouse System Integration
- Debug system integration with trace/log/debug/warn functions
- Error reporting through Henhouse error system
- Gateway access for configuration
- Standard Henhouse database connection patterns

### Extensibility
- Plugin architecture for new decorators
- Automatic discovery of new decorator modules
- Integration with Henhouse configuration management
- Uses Henhouse caching patterns

## Configuration

### Global Decorators
Apply decorators to all processed content:

```python
# Apply first decorator to all elements, then use parser output
processor = TextProcessor(
    first_decorator='uppercase',  # Applied to every element first
    final_decorator='parser'      # Final conversion to CLI tables
)

# Common pattern: just specify final output format
processor = TextProcessor(final_decorator='mcp')  # Default
processor = TextProcessor(final_decorator='parser')  # CLI tables
```

### Decorator Discovery
Discovers decorators by:
1. Scanning the `hh` module tree for `@register_tp_decorator` decorators
2. Caching discovery results in JSON files
3. Lazy loading decorators when needed
4. Validating cached decorators on each use

The system uses standard Henhouse `.ini` files (`icon.ini`, `label.ini`) for display configuration in CLI output, following the same patterns as other Henhouse modules.

### Performance Tuning
- Cache management for size and refresh frequency
- Lazy loading of decorators
- Module validation before use
- Error handling configuration

## Best Practices

### Decorator Design
- Pure functions without side effects
- Idempotent - multiple applications are safe
- Handle invalid inputs gracefully
- Provide clear docstrings and examples

### Content Organization
- Use consistent markup patterns
- Validate content before processing
- Use appropriate decorators for the task
- Test decorators with various inputs

### Database Integration
- Use proper database transactions
- Handle database errors gracefully
- Clean up old data before adding new
- Validate page/image existence before processing






## Link Tokens

- `[[page_id]]`
- `[[page_id][name_override]]`
- `[[page_link]]`
- `[[page_link][name_override]]`

```json
{
	"type": "page_link",
	"resolved_page": {
		"id": 123456,
		"parent": 1,
		"name": "Page Name",
		"name_override": "Custom Page Name"			// optional field, only add if supplied
	}
}
```

## Image Tokens

- `{{page_id}}`
- `{{page_id}{caption_override}}`
- `{{page_link}}`
- `{{page_link}{caption_override}}`
- `{{{image_id}}}`
- `{{{image_id}}{caption_override}}`

```json
{
	"type": "image",
	"resolved_image": {
		"id": 7890,
		"filename": "image.jpg",
		"path": "/images/",
		"caption": "Original Caption",
		"caption_override": "Custom Caption Text",		// optional field
		"instances": [
			{
				"width": 1200,
				"height": 1200,
				"src": "2024/10/27/image.jpg",
				"filesize": 245760
			},
			{
				"width": 700,
				"height": 700,
				"src": "2024/10/27/image_large.jpg",
				"filesize": 120000
			},
			{
				"width": 300,
				"height": 300,
				"src": "2024/10/27/image_small.jpg",
				"filesize": 45000
			},
			{
				"width": 100,
				"height": 100,
				"src": "2024/10/27/image_thumb.jpg",
				"filesize": 15000
			}
		]
	}
}
```

## Image Link Tokens

- `[[page_id]{{}}]`											// default to same as page id
- `[[page_id]{{}}{caption_override}]`						// etc
- `[[page_id][{{other_page_id}}]]`
- `[[page_id][{{other_page_id}{caption_override}}]]`
- `[[page_id][{{{image_id}}}]]`
- `[[page_id][{{{image_id}}{caption_override}}]]`
- `[[page_link]{{}}]`										// default to same as page_link
- `[[page_link]{{}{caption_override}}]`						// etc
- `[[page_link][{{other_page_name}}]]`
- `[[page_link][{{other_page_name}{caption_override}}]]`
- `[[page_link][{{{image_id}}}]]`
- `[[page_link][{{{image_id}}{caption_override}}]]`

```json
{
	"type": "image_link",
	"resolved_page": {
		"id": 123456,
		"parent": 1,
		"name": "Page Name",
		"resolved_image": {
			"type": "image",
			"resolved_image": {
				"id": 7890,
				"filename": "image.jpg",
				"path": "/images/",
				"caption": "Original Caption",
				"caption_override": "Custom Caption Text",		// optional field
				"instances": [
					{
						"width": 1200,
						"height": 1200,
						"src": "2024/10/27/image.jpg",
						"filesize": 245760
					},
					{
						"width": 700,
						"height": 700,
						"src": "2024/10/27/image_large.jpg",
						"filesize": 120000
					},
					{
						"width": 300,
						"height": 300,
						"src": "2024/10/27/image_small.jpg",
						"filesize": 45000
					},
					{
						"width": 100,
						"height": 100,
						"src": "2024/10/27/image_thumb.jpg",
						"filesize": 15000
					}
				]
			}
		}
	}
}
```

## Decorator Chain Tokens 

- `@pi(5)`
- `@echo('Hello, World!')`


```json
{
	"type": "custom",
	"value": "3.14159"|"Hello, World!"
}
```
