# TextProcessor System

A text processing system that transforms structured markup into formatted output through a decorator-based pipeline architecture.

## Overview

TextProcessor transforms structured markup into output formats using a decorator pipeline pattern. Text flows through a series of transformation functions for formatting, translation, and output generation.

## Core Architecture

### Pipeline Processing Model

TextProcessor uses a **pipeline architecture** where text flows through decorators in a specific order:

```
Input Text → Parse → Generate JSON → First Decorator → User Decorators (reversed) → Final Decorator → Output
```

Note: User decorators are applied in **reverse order** (right-to-left) - the last decorator in the chain is applied first.

Each decorator is a pure function that receives text input and returns transformed text output.

### Format-Agnostic Design

The system generates different output formats by changing the final decorator:
- See `hh/tp/tp.py` - `TextProcessor.__init__()` and `_apply_final_decorator()` methods
- JSON output (default): `TextProcessor(final_decorator='mcp')` - See `hh/tp/tp_decorators.py` - `mcp_decorator()` function
- CLI table output: `TextProcessor(final_decorator='parser')` - See `hh/tp/tp_decorators.py` - `parser_decorator()` function
- Same input produces different outputs based on final decorator selection

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
Decorators are parsed **left-to-right** but applied **right-to-left** (reversed):
```
@hero @center @border {{link name}}
```
Parsed as: `[('hero', {}), ('center', {}), ('border', {})]`
Applied as: `hero(center(border(base_text)))` (rightmost decorator applied first, then leftward)

**Chaining Rules**:
- Decorators must be separated by exactly one whitespace character
- Multiple whitespace characters break the chain
- Chain continues until no more `@` decorators or base elements are found

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
  - Default precision is 5 if not provided or invalid

- **`@echo(text)`** - Returns the provided text as custom value
  - `@echo('Hello')` → `{"type": "custom", "value": "Hello"}`
  - If no arg0 provided, uses the input text parameter

### Transformation Decorators
- **`@repeat(count, separator)`** - Repeats custom value with optional separator
  - `@repeat(3, ', ')` on custom value → repeats it 3 times with separator
  - Only works with `{"type": "custom"}` structures, returns original if not custom type

- **`@precision(decimals)`** - Formats decimal numbers in custom values
  - `@precision(2)` on numeric custom value → formats to 2 decimal places
  - Only works with `{"type": "custom"}` structures, returns original if not custom type or not numeric

### Final Output Decorators
- **`@mcp`** - Converts internal structure to JSON string (default final decorator if none specified)
- **`@parser`** - Converts internal structure to CLI table format
- **`@http`** - Converts internal structure to HTML format (hyperlinks and image tags)

Note: Most decorators work with internal JSON structures (`{"type": "...", "value": "..."}`) and pass them through the pipeline. Final decorators (`@mcp`, `@parser`, `@http`) convert these structures to string output. Regular decorators return dict, final decorators return str.

## Technical Implementation

### Core Classes

#### TextProcessor
Main processing class - See `hh/tp/tp.py`:
- `__init__(first_decorator=None, final_decorator=None)` - Initialize with optional global decorators
- `process(content: str) -> Optional[str]` - Main processing method, returns None if preprocessing fails
- `preprocess(content: str)` - Parses and resolves markup, returns list of JSON structures
- `postprocess(preprocessed_elements, final_decorator=None)` - Applies decorators and final formatting
- `update_links_table(conn, page_id: int) -> bool` - Database integration for link management

#### Decorator Registry
Manages decorator discovery and loading - See `hh/tp/tp_decorator_registry.py`:
- `@register_tp_decorator('decorator_name')` - Registration decorator pattern
- `get_tp_decorator(name: str)` - Retrieves decorator function from registry
- Decorator function signature: `def decorator_name(json_data: Union[str, Dict[str, Any]], **kwargs: Any) -> Union[str, Dict[str, Any]]`
- Regular decorators return `Dict[str, Any]` (JSON structure), final decorators return `str` (formatted output)
- See `hh/tp/tp_decorators.py` for built-in decorator examples

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

- **`links` table** - Stores page-to-page references (columns: `id`, `link`, `resolution_id`)
- **`image_links` table** - Stores page-to-image references (columns: `id`, `resolution_id`)
- **Automatic cleanup** - Removes old links before adding new ones (DELETE FROM links/image_links WHERE id = page_id)
- **Link types stored**:
  - Direct page ID links: `[[123456]]` → `links` table
  - Page name links: `[[Home]]` → `links` table (resolved to page ID)
  - Direct image ID references: `{{{7890}}}` → `image_links` table
  - Nested image in link display: `[[page][{{{image_id}}}]]` → both `links` and `image_links` tables
  - Page image references: `{{page_id}}` or `{{page_name}}` → `links` table (page reference for image display)

#### Page Resolution
- **Page ID lookup** - Uses `get_page(page_id=page_id)` from page registry
- **Page name lookup** - Uses `find_page(link=page_name)` from page registry
- **Image ID lookup** - Uses `get_image(image_id)` from image registry
- **Primary image lookup** - Queries `image_groups` table for `image_rank=1` to find page's primary image
- **Error handling** - Missing pages/images add to `_parse_errors` list, return placeholder data (page_id=0, name="Page {id} (not found)")

### Performance Features

#### Caching System
- JSON-based caching for decorator discovery (cache file: `hh/tp/cache/tp-decorators.json`)
- Hot cache: `_global_registry` dictionary in memory (populated at import time)
- Cold cache: JSON file with decorator metadata (module path, function name, load status)
- Lazy loading: Decorators loaded from cold cache on first use via `get_tp_decorator()`
- Cache rebuild: On cache miss, `discover_tp_decorators(force_regenerate=True)` scans all `@register_tp_decorator` decorators
- Module validation: Cached module paths validated via `_validate_cached_module_path()` before use
- Deployed decorators: Also scans `/srv/{project_name}/site/py` for deployed decorator files (file:// paths)

#### Error Handling
- Parse error collection with detailed messages (stored in `_parse_errors` list)
- Parse errors reported via `report_error("link_resolution", error_msg)` - if errors exist, `preprocess()` returns `None` and `process()` returns `None`
- Database error handling for resolution failures (reported via `report_error("link_resolution", ...)`)
- Decorator error handling with graceful fallbacks (reported via `report_error("textprocessor", ...)`, returns original json_data on error)
- Logging at all processing levels via debug system (trace_in/trace_out, log, debug, warn)

## Usage Examples

### Basic Text Processing
See `hh/tp/tp.py` - `TextProcessor` class:
- `TextProcessor()` - Simple processing (defaults to JSON output via 'mcp' final decorator)
- `TextProcessor(final_decorator='parser')` - CLI table output
- `process()` method - Main processing method that handles text with markup
- Pure decorator examples: `@pi(5)`, `@echo('text')` - See `hh/tp/tp_decorators.py` for built-in decorators

### Format-Specific Processing
See `hh/tp/tp.py` - `TextProcessor` class:
- JSON output: `TextProcessor()` or `TextProcessor(final_decorator='mcp')` - See `hh/tp/tp_decorators.py` - `mcp_decorator()` function
- CLI table output: `TextProcessor(final_decorator='parser')` - See `hh/tp/tp_decorators.py` - `parser_decorator()` function
- HTML output: `TextProcessor(final_decorator='http')` - See `hh/tp/tp_decorators.py` - `http_decorator()` function

### Database Integration
See `hh/page/page_content.py` - `PageContentMixin.modify_text()` method:
- TextProcessor integration with database connection via `gateway.conn`
- `processor.update_links_table(gateway.conn, page_id)` - Updates `links` and `image_links` tables
- Connection uses standard Henhouse Connection class methods (`read()`, `create()`, `delete()`)

### Custom Decorators
See `hh/tp/tp_decorators.py` for example decorator implementations:
- `@register_tp_decorator('decorator_name')` - Registration pattern
- `hh/tp/tp_image_decorators.py` - Image-specific decorators
- `hh/tp/other_decorators.py` - Additional decorator examples
- Decorator function signature: `def decorator_name(json_data: Union[str, Dict[str, Any]], **kwargs: Any) -> Union[str, Dict[str, Any]]`

## Advanced Features

### Decorator Argument Parsing
Decorators receive arguments as `arg0`, `arg1`, `arg2`, etc. in `kwargs`:
- See `hh/tp/tp.py` - `_parse_decorator_arguments()` method for argument parsing logic
- See `hh/tp/tp_decorators.py` - `pi_decorator()`, `echo_decorator()`, `repeat_decorator()` for examples of argument access
- Argument access pattern: `kwargs.get('arg0')`, `kwargs.get('arg1')`, etc.

### Nested Element Support
Supports nested structures (links within images, decorators on nested elements):
- See `hh/tp/tp.py` - `_parse_unparsed_text()`, `_parse_decorated_element()`, `_parse_base_element()` methods for parsing logic
- Nested parsing handles: `[[page][{{image}{caption}}]]`, `@decorator [[link]]`, etc.

### Error Recovery
Provides error handling:

- Parse errors are collected and reported
- Database errors are logged with context
- Decorator errors fall back to original text
- Missing pages/images are handled gracefully

## Integration Points

### Henhouse System Integration
- Debug system integration with trace/log/debug/warn functions (via `register_debug_init`) - See `hh/tp/tp.py` - `_initialize_debug()` function
- Error reporting through Henhouse error system (`report_error("textprocessor", ...)` and `report_error("link_resolution", ...)`) - See `hh/tp/tp.py` throughout for error reporting
- Gateway access for database connections: Uses `get_gateway().conn` for internal lookups (e.g., primary image lookup) - See `hh/tp/tp.py` - `_resolve_image_info()` method
- Database connection parameter: `update_links_table(conn, page_id)` receives Connection instance from caller - See `hh/page/page_content.py` - `PageContentMixin.modify_text()` for usage pattern
- Standard Henhouse database connection patterns (Connection class with `read()`, `create()`, `delete()` methods)
- Page registry integration (`get_page()`, `find_page()`) - See `hh/tp/tp.py` - `_resolve_link_info()` and `_resolve_image_info()` methods
- Image registry integration (`get_image()`) - See `hh/tp/tp.py` - `_resolve_image_info()` method

### Extensibility
- Plugin architecture for new decorators
- Automatic discovery of new decorator modules
- Integration with Henhouse configuration management
- Uses Henhouse caching patterns

## Configuration

### Global Decorators
Apply decorators to all processed content:
- See `hh/tp/tp.py` - `TextProcessor.__init__()` method for `first_decorator` and `final_decorator` parameters
- `first_decorator` - Applied to every element first (before user decorators)
- `final_decorator` - Final conversion to output format ('mcp' for JSON, 'parser' for CLI tables, 'http' for HTML)
- Common pattern: `TextProcessor(final_decorator='parser')` for CLI table output

### Decorator Discovery
Discovers decorators by:
1. Scanning the `hh` module tree recursively for files containing `@register_tp_decorator` decorators
2. Also scanning `/srv/{project_name}/site/py` for deployed decorator files (file:// paths)
3. Importing modules to populate `_global_registry` dictionary
4. Caching discovery results in JSON file (`hh/tp/cache/tp-decorators.json`) with module path, function name, load status
5. Lazy loading decorators when needed via `get_tp_decorator()` (checks hot cache first, then cold cache, then rebuilds)
6. Validating cached decorators on each use via `_validate_cached_module_path()` (tries to import module)

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
