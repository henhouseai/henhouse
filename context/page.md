# Page System Architecture Documentation

This document covers the core business logic modules for page, image, and text processing in the Python Gateway-based system. For Gateway, Registry, Render, and other infrastructure details, see the respective documentation files.

## Table of Contents

1. [Page Module](#1-page-module)
2. [Image Module](#2-image-module)
3. [Text Processor Module](#3-text-processor-module)

## Agent Quick Reference

- **Core Modules**: `page/` (hierarchical content), `image/` (media management), `tp/` (markup parsing)
- **Mixin Architecture**: Page class uses 9 mixins with direct database access via `self.gateway.conn`
- **Cache System**: Five derived fields (display_name, prepared_text, children_by_class, images, files) cached in separate cache database
- **Page Registry**: Hot cache system with automatic cache refresh during gateway commit
- **Page Class Registry**: Dynamic subclass loading based on page class field
- **Markup Language**: `[[page_links]]`, `{{image_embeds}}`, decorator-based processing
- **Page Hierarchy**: Parent-child relationships with automatic breadcrumb generation
- **Image Instances**: Automatic multi-size generation and management
- **Text Processing**: Decorator-based parsing with configurable decorator registry

## Agent Training Notes

### Module Integration
- **Page Objects**: Actions create Page instances via `get_page(page_id)` from page registry
- **Image Objects**: Actions create Image instances for media operations
- **Text Processing**: Page content parsed through TextProcessor with decorator registry
- **Mixin Pattern**: Pages use multiple mixins for functionality
- **Display Methods**: Call `show_page()` for formatted output data

### Common Usage Patterns
- **Page Creation**: `get_page(page_id)` loads from hot cache or database
- **Image Management**: `Image(image_id)` handles multi-size instances automatically
- **Content Parsing**: TextProcessor decorators parse custom markup syntax
- **Data Retrieval**: All modules load from database via `gateway.conn` methods

---

## 1. Page Module

**Files**: `hh/page/*.py`

The hierarchical page management system with CRUD operations, display logic, and content processing. Provides a clean object-oriented interface using mixins for functionality.

### Page Class

#### owned by:
- action handlers : *Created by page actions (add_page, show_page, etc.)*

#### owns:
- page data : *Page content, metadata, hierarchy information*
- validation logic : *Page validation and constraint checking*
- hierarchy logic : *Parent-child relationship management*
- content logic : *Text processing and parsing*
- image logic : *Image association management*
- file logic : *File association management*
- display logic : *Output data preparation*
- cache logic : *Cache database management*

#### data managed:
- page metadata (source of truth) : *ID, name, link, parent, class, visibility*
- content data (source of truth) : *Text content and parsed HTML*
- hierarchy data (source of truth) : *Parent-child relationships*
- image associations (source of truth) : *Linked images*
- file associations (source of truth) : *Linked files*
- display data (source of truth) : *Rendered output data for backends*
- cache data (source of truth) : *Five derived fields in cache database*

#### calls:
- **Validation mixins** : *PageValidationMixin for constraints*
- **Hierarchy mixins** : *PageHierarchyMixin for tree operations*
- **Content mixins** : *PageContentMixin for content handling*
- **Image mixins** : *PageImagesMixin for image operations*
- **File mixins** : *PageFilesMixin for file operations*
- **Display mixins** : *PageDisplayMixin for output preparation*
- **AJAX mixins** : *PageAjaxMixin for JSON payload assembly*
- **Cache mixins** : *PageCacheMixin for cache management*
- **Maintenance mixins** : *PageMaintenanceMixin for maintenance operations*

#### called by:
- action handlers : *Actions create Page instances and call methods*
- backend handlers : *Backends receive Page data for formatting*

#### retrieves from:
- database : *Gets page info from pages table via gateway.conn*
- cache database : *Gets cached derived fields from cache database*
- text processor : *Gets parsed content from TextProcessor*

#### provides to:
- action handlers : *Provides Page objects with methods*
- backend handlers : *Provides structured page data for rendering*

#### configuration dependencies:
- hh/page/*.py : *Page module implementation files*

#### agent training notes:
- **Page Creation**: Actions call `get_page(page_id)` from page registry which loads from hot cache or database
- **Data Loading**: Page constructor loads data automatically on init and hydrates from cache if available
- **Mixin Methods**: Page uses nine mixins with direct database access via `self.gateway.conn`
- **Connection Management**: All mixin methods use `self.gateway.conn` directly (no decorators or wrappers)
- **Cache System**: Five derived fields (display_name, prepared_text, children_by_class, images, files) are cached in separate cache database
- **Cache Refresh**: Cache refresh happens automatically during gateway commit via `refresh_stale_page_caches()`
- **Display Data**: Call `show_page()` for formatted output data
- **Action Pattern**: Page actions use @register_action decorator

### Mixin Architecture

The Page class uses multiple inheritance with nine specialized mixins, each providing focused functionality. All mixin methods access the database directly through `self.gateway.conn`.

#### The Nine Mixins

1. **PageValidationMixin** (`page_validation.py`)
   - **Purpose**: Name validation, move validation, duplicate checking
   - **Key Methods**: `validate_name()`, `can_move_to_page()`, `check_children_recursive()`
   - **Class Methods**: `allow_null_names()`, `allow_duplicate_names()`, `auto_link_name()`, `allow_inside_of()`
   - **Instance Methods**: `allow_class_inside()`

2. **PageHierarchyMixin** (`page_hierarchy.py`)
   - **Purpose**: Parent-child relationships, breadcrumbs, move/copy operations
   - **Key Methods**: `get_path()`, `get_children_data()`, `get_child_page_ids()`, `move_page()`, `copy_page()`
   - **Static Methods**: `_get_children_query()` - can be overridden by subclasses to customize child queries
   - **Cache Fields**: `display_name` (computed via `_get_display_name()`)

3. **PageContentMixin** (`page_content.py`)
   - **Purpose**: CRUD operations, text processing, page data assembly
   - **Key Methods**: `modify_name()`, `modify_text()`, `add_page()`, `delete_page()`, `get_page_data()`, `flag_page_modification()`
   - **Class Hooks**: `_add_page_class_information()` - called after page creation for class-specific setup
   - **Instance Hooks**: `_delete_page_class_information()` - called before page deletion for cleanup
   - **Cache Fields**: `prepared_text` (computed via `get_prepared_text()`)

4. **PageImagesMixin** (`page_images.py`)
   - **Purpose**: Image association management, ranking, copying/moving images
   - **Key Methods**: `get_images_data()`, `add_image()`, `copy_images()`, `move_images()`, `set_image_rank()`, `remove_image()`
   - **Internal Methods**: `_create_image_record()`, `_add_image_to_group()`, `_reorder_images()`
   - **Cache Fields**: `images` (computed via `get_images_data()`)

5. **PageFilesMixin** (`page_files.py`)
   - **Purpose**: File association management, ranking, copying/moving files
   - **Key Methods**: `get_files_data()`, `add_file()`, `copy_files()`, `move_files()`, `set_file_rank()`, `remove_file()`
   - **Internal Methods**: `_create_file_record()`, `_add_file_to_group()`, `_reorder_files()`
   - **Cache Fields**: `files` (computed via `get_files_data()`)

6. **PageDisplayMixin** (`page_display.py`)
   - **Purpose**: Display data preparation, child grouping, badge headers
   - **Key Methods**: `show_page()`, `_get_children_by_class()`, `_get_children_for_class()`
   - **Hooks**: `_add_upper_content()`, `_add_lower_content()`, `_add_badge_headers()`, `_get_child_row_field_type()`
   - **Cache Fields**: `children_by_class` (computed via `_get_children_by_class()`)

7. **PageAjaxMixin** (`page_ajax.py`)
   - **Purpose**: AJAX-friendly JSON payload assembly for MCP backend
   - **Key Methods**: `get_page()` - returns minimal JSON structure with available actions

8. **PageCacheMixin** (`page_cache.py`)
   - **Purpose**: Cache database management for five derived fields
   - **Key Methods**: `_refresh_cached_page()`, `_ensure_cache_entry()`, `_flag_cache_refresh()`
   - **Cache Fields**: All five derived fields (display_name, prepared_text, children_by_class, images, files)

9. **PageMaintenanceMixin** (`page_maintenance.py`)
   - **Purpose**: Maintenance operations like regex text replacement
   - **Key Methods**: `regex_text()`

#### Database Access Pattern

All mixin methods access the database directly through `self.gateway.conn`:

```python
def some_mixin_method(self):
    trace_in()
    # Direct database access via gateway.conn
    results = self.gateway.conn.read("SELECT ...", [params])
    affected = self.gateway.conn.update("UPDATE ...", [params])
    new_id = self.gateway.conn.create("INSERT ...", [params])
    trace_out()
    return result
```

**Key Points**:
- All methods use `self.gateway.conn` directly
- No decorators or wrapper methods needed
- Connection is automatically managed by gateway
- Methods work within existing transactions

#### Cache System

The page system uses a two-tier cache system:

1. **Hot Cache** (`page_registry.py`): In-memory cache of Page instances
2. **Cache Database**: Separate database storing five derived fields

**Five Derived Fields** (cached in cache database):
- `display_name`: Computed display name
- `prepared_text`: Processed text content (JSON)
- `children_by_class`: Grouped children data (JSON)
- `images`: Image association data (JSON)
- `files`: File association data (JSON)

**Cache Hydration Flow**:
1. Page constructor loads base data from main database
2. Checks if cache exists and is fresh (cache_built_at >= last_modified)
3. If cache is fresh, hydrates five derived fields from cache database
4. If cache is stale or missing, fields remain empty and are computed on-demand

**Cache Refresh Flow**:
1. When derived fields are computed, `_flag_cache_refresh()` is called
2. During gateway commit, `refresh_stale_page_caches()` is called
3. For each flagged page, `_refresh_cached_page()` writes all five fields to cache database
4. Updates `cache_built_at` in main database

**Lazy Computation Pattern**:
```python
def get_images_data(self):
    # Check if field is already populated
    if hasattr(self, 'images') and self.images:
        return self.images
    # Field is empty, compute it
    images_data = []
    # ... compute from database ...
    self.images = images_data
    self._flag_cache_refresh()  # Flag for cache refresh
    return images_data
```

### Page Registry

**File**: `hh/page/page_registry.py`

The page registry manages hot cache and provides page loading functions.

#### Key Functions

- **`get_page(page_id: int)`**: Get page from hot cache or load from database
  - Checks hot cache first
  - If not found, determines page class and loads from database
  - Stores in hot cache for future access
  - Page constructor handles cache hydration automatically

- **`find_page(link: str)`**: Find page by link
  - Queries database for page with matching link
  - Returns page instance via `get_page()`

- **`refresh_stale_page_caches()`**: Refresh cache for all flagged pages
  - Called by gateway during commit process
  - Iterates through hot cache and refreshes pages with `_cache_needs_refresh` flag
  - Updates cache database with all five derived fields

#### Hot Cache Management

- Hot cache is a module-level dictionary: `_page_cache: Dict[int, Page]`
- Pages are stored in hot cache after first load
- Cache refresh happens during gateway commit
- No automatic expiration - pages remain in cache for request lifetime

### Page Class Registry

**File**: `hh/page/page_class_registry.py`

The page class registry manages dynamic subclass loading based on the `class` field in the database.

#### Key Functions

- **`register_page_class(class_name: str)`**: Decorator to register page subclasses
  - Used as `@register_page_class('class_name')` on Page subclasses
  - Registers class in global registry

- **`get_page_class(class_name: str)`**: Get Page subclass for a class name
  - Checks hot cache first
  - If not found, checks cold cache (JSON file)
  - If not found, rebuilds cold cache by scanning for `@register_page_class` decorators
  - Returns Page class or None (falls back to base Page class)

- **`discover_page_classes()`**: Scan codebase for page classes
  - Scans all Python files for `@register_page_class` decorators
  - Imports modules to populate registry
  - Caches results in JSON file

#### Dynamic Class Loading

When `get_page(page_id)` is called:
1. Queries database for page's `class` field
2. Calls `get_page_class(class_name)` to get appropriate subclass
3. Instantiates that subclass instead of base Page class
4. Subclass inherits all mixin functionality

---

## 2. Image Module

**Files**: `hh/image/*.py`

The image management system with CRUD operations, multi-size instance management, and display logic. Handles automatic image processing and intelligent sizing.

### Image Class

#### owned by:
- action handlers : *Created by image actions (add_image, show_image, etc.)*

#### owns:
- image data : *Image metadata and instance information*
- validation logic : *Image validation and constraints*
- instance logic : *Multi-size image management*
- display logic : *Output data preparation*

#### data managed:
- image metadata (source of truth) : *ID, caption, parent, visibility*
- instance data (source of truth) : *Multiple sized versions*
- file paths (source of truth) : *Physical file locations*
- display data (source of truth) : *Rendered output data for backends*

#### calls:
- **ImageValidationMixin** : *Validation logic*
- **ImageInstancesMixin** : *Multi-size management*
- **ImageContentMixin** : *Content operations*
- **ImageDisplayMixin** : *Output preparation*

#### called by:
- action handlers : *Actions create Image instances and call methods*
- backend handlers : *Backends receive Image data for formatting*

#### retrieves from:
- database : *Gets image data from images table*
- database : *Gets instance data from imageinstances table*
- file system : *Gets physical image files from /srv/images/*

#### provides to:
- action handlers : *Provides Image objects with methods*
- backend handlers : *Provides structured image data for rendering*

#### configuration dependencies:
- hh/image/*.py : *Image module implementation files*

#### agent training notes:
- **Image Creation**: Actions call `Image(image_id)` which loads metadata
- **Instance Management**: Images automatically manage multiple size instances
- **Display Data**: Call `_show_image()` to get formatted output data
- **Action Pattern**: Image actions use @register_action decorator

---

## 3. Text Processor Module

**Files**: `hh/tp/*.py` and `hh/tp/*.ini`

The custom markup parsing system for page content. Implements decorator-based processing with configurable decorator registry.

### TextProcessor Class

#### owned by:
- page system : *Created by Page class for content processing*

#### owns:
- parse state : *Current parsing position and context*
- decorator registry : *Registered decorators for processing*
- parse results : *Processed HTML content*

#### data managed:
- parse state (source of truth) : *Current parsing position in text*
- decorator registry (source of truth) : *Registered decorators and configuration*
- parse results (source of truth) : *Processed HTML content output*

#### calls:
- **process_text()** : *Main processing function*
- **decorator registry** : *Applies registered decorators*
- **parse syntax** : *Parses custom markup syntax*

#### called by:
- page system : *Pages call TextProcessor for content parsing*
- action handlers : *Actions may call for text rendering*

#### retrieves from:
- page content : *Gets page text data*
- decorator config files : *Gets decorator configuration from .ini files*

#### provides to:
- page system : *Provides parsed HTML content*
- backend handlers : *Provides processed text for rendering*

#### configuration dependencies:
- hh/tp/*.ini files : *Decorator configuration (icon.ini, label.ini)*
- hh/tp/decorators.py : *Decorator implementations*

#### agent training notes:
- **Text Processing**: Use TextProcessor for all content processing
- **Decorator Pattern**: Decorators are registered automatically and applied in order
- **Markup Syntax**: Supports [[links]], {{images}}, and other custom syntax
- **INI Configuration**: Decorators configured in .ini files in tp/ directory

---

## Integration with Other Systems

### With Gateway (see gateway.md)
- Actions create Page/Image instances and call mixin methods
- Actions return JSON via `gateway.response.set_action_response()`
- Backends receive Page/Image JSON data for formatting
- Cache refresh happens during gateway commit

### With Registry (see registry.md)
- Page/Image actions use @register_action decorator
- Backends use appropriate @register_parser/@register_http/@register_mcp decorators
- Handlers auto-discovered and registered

### With Render System (see render.md)
- Backends use render functions to format Page/Image data
- Page/Image display data structure compatible with render system
- FieldConfig used for table formatting

### Database Access Pattern
- All modules use `gateway.conn` methods directly
- Page/Image mixins call `gateway.conn.read()`, `gateway.conn.create()`, `gateway.conn.update()`, `gateway.conn.delete()`
- Cache operations use `gateway.conn.read_cache()`, `gateway.conn.create_cache()`, `gateway.conn.update_cache()`
- Tier-based credentials loaded from ~/.project.cnf files

---

This document focuses specifically on the page, image, and text processor business logic modules. For infrastructure details (Gateway, Registry, Render), see the respective documentation files.
