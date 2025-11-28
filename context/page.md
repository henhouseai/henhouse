# Page System Architecture Documentation

This document covers the core business logic modules for page, image, and text processing in the Python Gateway-based system. The Page system is the **extensible infrastructure** upon which all content management is built. It provides a hierarchical content management system with CRUD operations, display logic, and content processing, designed from the ground up to be extended through derived classes.

For Gateway, Registry, Render, and other infrastructure details, see the respective documentation files.

## Table of Contents

1. [Page Module](#1-page-module)
   - [Core Architecture](#core-architecture)
   - [The Five Validation Functions](#the-five-validation-functions)
   - [Extensibility System](#extensibility-system)
   - [CRUD Operations](#crud-operations)
   - [The Nine Mixins](#the-nine-mixins)
   - [Cache System](#cache-system)
   - [Page Registry](#page-registry)
   - [Page Class Registry](#page-class-registry)
2. [Image Module](#2-image-module)
3. [Text Processor Module](#3-text-processor-module)

## Agent Quick Reference

- **Core Modules**: `page/` (hierarchical content), `image/` (media management), `tp/` (markup parsing)
- **Mixin Architecture**: Page class uses 9 mixins with direct database access via `self.gateway.conn`
- **Extensibility**: Base Page class designed for inheritance; derived classes override validation functions, hooks, and display methods
- **Cache System**: Five derived fields (display_name, prepared_text, children_by_class, images, files) plus main DB metadata cached in separate cache database
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

The hierarchical page management system with CRUD operations, display logic, and content processing. Provides a clean object-oriented interface using mixins for functionality. **The Page system is designed as extensible infrastructure** - the base `Page` class provides core functionality, while derived classes extend it for specific content types (source code files, work pages, etc.).

### Core Architecture

The Page class is a composite of nine specialized mixins, providing a modular architecture that can be extended through inheritance. All mixin methods access the database directly through `self.gateway.conn`.

#### Page Class Structure

The Page class is defined in `hh/page/page.py` and inherits from nine mixins. See the class definition for the complete mixin list.

#### Metadata Extraction

The Page constructor automatically extracts metadata fields as object attributes, enabling derived classes to store custom data in the metadata JSON field and access it directly. See `Page.__init__()` in `hh/page/page.py` (around lines 115-127) for the extraction logic.

**Key Points**:
- Metadata fields are automatically extracted as `self.attribute_name`
- Existing Page attributes are protected (metadata won't overwrite them)
- Derived classes can store custom fields in metadata and access them directly
- Example: `SourceCodeFile` stores `file_path` and `language` in metadata, accessible as `self.file_path` and `self.language`

#### Database Access Pattern

All mixin methods access the database directly through `self.gateway.conn`. See any mixin method (e.g., `modify_name()` in `PageContentMixin`) for examples.

**Key Points**:
- All methods use `self.gateway.conn` directly
- No decorators or wrapper methods needed
- Connection is automatically managed by gateway
- Methods work within existing transactions

### The Five Validation Functions

The Page system provides **five validation functions** that control page behavior and hierarchy constraints. These are the primary extension points for derived classes to customize validation rules.

All five functions are defined in `PageValidationMixin` and can be overridden by derived classes:

#### 1. `allow_null_names()` - Class Method

**Signature**: `@classmethod def allow_null_names(cls) -> bool`

**Default**: Returns `False` (names required)

**Purpose**: Determines if pages of this class can have `NULL` names in the database.

**When to Override**: 
- Set to `True` for classes that don't require names (e.g., `SourceCodeFile`, `WorkDocket`)
- Set to `False` for classes that must have names (e.g., base `Page`)

**Example Override**: See `SourceCodeFileValidationMixin.allow_null_names()` in `hh/source_code_file/source_code_file_validation.py`

#### 2. `allow_duplicate_names()` - Class Method

**Signature**: `@classmethod def allow_duplicate_names(cls) -> bool`

**Default**: Returns `True` (duplicates allowed)

**Purpose**: Determines if multiple pages of this class can have the same name under the same parent.

**When to Override**:
- Set to `False` to enforce unique names within a parent (rare)
- Keep `True` for most use cases

**Example Override**: See `SourceCodeFileValidationMixin.allow_duplicate_names()` in `hh/source_code_file/source_code_file_validation.py`

#### 3. `auto_link_name()` - Class Method

**Signature**: `@classmethod def auto_link_name(cls) -> bool`

**Default**: Returns `True` (auto-link enabled)

**Purpose**: Determines if the `link` field should automatically be set to match the `name` field when a page is created or renamed.

**When to Override**:
- Set to `False` for classes that manage links manually (e.g., `SourceCodeFile`, `WorkDocket`)
- Keep `True` for simple pages where name and link should match

**Example Override**: See `SourceCodeFileValidationMixin.auto_link_name()` in `hh/source_code_file/source_code_file_validation.py`

#### 4. `allow_class_inside()` - Instance Method

**Signature**: `def allow_class_inside(self, target_class: str) -> bool`

**Default**: Returns `True` (can contain any class)

**Purpose**: Determines if **this page instance** can contain child pages of the specified `target_class`.

**When to Override**:
- Restrict which child classes are allowed under this page type
- Example: Work dockets might only allow "ask" children

**Example Override**: See `SourceCodeFileValidationMixin.allow_class_inside()` in `hh/source_code_file/source_code_file_validation.py`

#### 5. `allow_inside_of()` - Class Method

**Signature**: `@classmethod def allow_inside_of(cls, parent_class: str) -> bool`

**Default**: Returns `True` (can be inside any class)

**Purpose**: Determines if pages of **this class** can be created inside pages of the specified `parent_class`.

**When to Override**:
- Enforce hierarchy constraints (e.g., "asks can only be inside work dockets")
- Prevent abstract classes from being instantiated directly

**Example Override** (Abstract Class): See `WorkPageValidationMixin.allow_inside_of()` in `hh/work/work_page_validation.py` - prevents abstract class from being instantiated directly.

**Example Override** (Hierarchy Constraint): See `WorkDocketValidationMixin.allow_inside_of()` in `hh/work_docket/work_docket_validation.py`

#### Validation Function Usage

These functions are called during:
- **Page Creation** (`add_page()`): Checks `allow_null_names()`, `allow_duplicate_names()`, `allow_class_inside()`, `allow_inside_of()`
- **Name Modification** (`modify_name()`): Checks `allow_null_names()`, `allow_duplicate_names()`, `auto_link_name()`
- **Move Operations** (`move_page()`): Checks `allow_class_inside()` and `allow_inside_of()`

See `PageValidationMixin.validate_name()` in `hh/page/page_validation.py` for the full implementation that uses these functions.

### Extensibility System

The Page system is designed for extension through inheritance. Derived classes can override validation functions, hooks, and display methods to customize behavior.

#### Creating Derived Classes

Derived classes extend `Page` (or intermediate abstract classes) and add their own mixins:

**Simple Derived Class Example**: See `SourceCodeFile` class in `hh/source_code_file/source_code_file.py` - extends Page directly with validation and content mixins.

**Abstract Intermediate Class Example**: See `WorkPage` class in `hh/work/work_page.py` - abstract base class that extends Page and provides shared functionality (status, meta, sort_order) for work entities.

**Concrete Derived Class Example**: See `WorkDocket` class in `hh/work_docket/work_docket.py` - extends WorkPage (which extends Page) with work docket-specific validation and content mixins.

#### Inheritance Patterns

**Pattern 1: Direct Extension** (Simple)
- `Page` → `SourceCodeFile`
- Adds file_path and language fields
- Overrides validation functions and display name

**Pattern 2: Abstract Intermediate** (Multi-tier)
- `Page` → `WorkPage` (abstract) → `WorkDocket` → `Ask` → `Task` → `Step`
- `WorkPage` provides shared functionality (status, meta, sort_order)
- Each tier adds specific constraints via validation functions
- Example hierarchy: Work dockets contain asks, asks contain tasks, tasks contain steps

#### Extension Points

Derived classes can override the following methods to customize behavior:

##### Class Hooks

**`_add_page_class_information(new_page_id: int)`** - Class Method
- Called after page creation for class-specific setup
- Use for initializing related records or setting defaults
- Example: Creating related records in other tables

**`_delete_page_class_information()`** - Instance Method
- Called before page deletion for cleanup
- Use for deleting related records or cleaning up resources

See `PageContentMixin._add_page_class_information()` and `_delete_page_class_information()` in `hh/page/page_content.py` for the base implementations.

##### Display Hooks

**`_get_display_name()`** - Instance Method
- Override to customize how page names are displayed
- Default: Returns `self.name` or `f"Page {self.id}"`
- Example: See `SourceCodeFileContentMixin._get_display_name()` in `hh/source_code_file/source_code_file_content.py` for an override that extracts filename from `file_path` when name is null

**`_add_upper_content()`** - Instance Method
- Override to add content above the main page content
- Returns `List[str]` of HTML/content strings
- Default: Returns empty list

**`_add_lower_content()`** - Instance Method
- Override to add content below the main page content
- Returns `List[str]` of HTML/content strings
- Default: Returns empty list

**`_add_badge_headers()`** - Instance Method
- Override to customize badge headers displayed above page content
- Returns `Dict[str, Any]` with badge data
- Default: Returns page summary badge
- See `PageDisplayMixin._add_badge_headers()` in `hh/page/page_display.py` for base implementation

**`_get_child_row_field_type()`** - Instance Method
- Override to customize the field type/icon shown when this page appears as a child in tables
- Returns string field type (used for rendering icons/labels)
- Default: Returns `'page'`
- Example: See `WorkDocketContentMixin._get_child_row_field_type()` in `hh/work_docket/work_docket_content.py` for status-based field types

##### Hierarchy Hooks

**`_get_children_query(parent_id: int)`** - Static Method
- Override to customize which children are returned and how they're ordered
- Returns tuple of `(query_string, params_list)`
- Default: Returns only 'page' class children, sorted by name
- Example: See `WorkDocketContentMixin._get_children_query()` in `hh/work_docket/work_docket_content.py` for custom ordering by metadata sort_order

**`_copy_page_class_information(new_page_id: int)`** - Instance Method
- Override to customize what happens when a page is copied
- Called during `copy_page()` operation
- Default: No-op

#### Custom Metadata Namespaces

Derived classes can use the metadata JSON field to store custom data. The Page constructor automatically extracts metadata fields as attributes, so derived classes can access them directly:

**Example**: `WorkPage` stores `status`, `meta`, and `sort_order` in metadata:
- These are automatically available as `self.status`, `self.meta`, `self.sort_order`
- Derived classes like `WorkDocket` inherit this behavior
- The `WorkPageContentMixin` provides methods to modify these fields

### CRUD Operations

Page CRUD operations follow a consistent pattern across all actions. Most actions use `show_page()` as their standard output format.

#### Action Pattern

All page actions follow this structure:

1. **Registration**: Use `@register_action` and `@register_command` decorators
2. **Argument Validation**: Check required arguments via `gateway.is_set()` and `gateway.get_arg()`
3. **Page Loading**: Load page via `get_page(page_id)` from registry
4. **Operation**: Call mixin method on page instance (e.g., `page.modify_name()`, `page.add_page()`)
5. **Response**: Call `page.show_page()` and set action response
6. **Error Handling**: Use `is_error()` and `report_error()` throughout

#### Standard CRUD Flow

**Example**: See `modify_name()` function in `hh/page/modify_name.py` for a complete example of the standard CRUD action pattern.

**Key Pattern**: After the operation, all actions call `page.show_page()` and set it as the action response. This provides consistent output format across all CRUD operations.

#### Standard Output: `show_page()`

The `show_page()` method is the standard output format for page operations. It returns a comprehensive dictionary with:

- `page`: Page metadata (id, name, link, parent, class, etc.)
- `children_by_class`: Grouped children data by class
- `images`: Associated images with ranks
- `files`: Associated files with ranks
- `badge_headers`: Badge data for display
- `upper_content`: Additional content above main content
- `lower_content`: Additional content below main content

See `PageDisplayMixin.show_page()` in `hh/page/page_display.py` for the full implementation. For MCP backend, it returns a lightweight payload without badge headers and extra content.

### The Nine Mixins

The Page class uses multiple inheritance with nine specialized mixins, each providing focused functionality. All mixin methods access the database directly through `self.gateway.conn`.

#### 1. PageValidationMixin (`page_validation.py`)

**Purpose**: Name validation, move validation, duplicate checking, hierarchy constraints

**Key Methods**:
- `validate_name(name, page_class, exclude_id, error_on_invalid)` - Validates page name using the five validation functions
- `can_move_to_page(target_page_id)` - Validates if page can be moved to target
- `check_children_recursive()` - Recursively gets all descendant page IDs

**Extension Points**:
- Override the five validation functions (`allow_null_names()`, `allow_duplicate_names()`, `auto_link_name()`, `allow_class_inside()`, `allow_inside_of()`)

**Code Reference**: `hh/page/page_validation.py`

#### 2. PageHierarchyMixin (`page_hierarchy.py`)

**Purpose**: Parent-child relationships, breadcrumbs, move/copy operations

**Key Methods**:
- `get_path()` - Returns breadcrumb path from root to this page
- `get_children_data()` - Returns full child page data
- `get_child_page_ids()` - Returns list of child page IDs
- `move_page(target_page_id)` - Moves page to new parent
- `copy_page(target_page_id, recursive, max_depth)` - Copies page with optional recursion
- `_get_display_name()` - Computes display name (cached in `display_name` field)

**Extension Points**:
- Override `_get_children_query(parent_id)` to customize child queries and ordering
- Override `_get_display_name()` to customize display name computation
- Override `_copy_page_class_information(new_page_id)` to customize copy behavior

**Cache Fields**: `display_name` (computed via `_get_display_name()`)

**Code Reference**: `hh/page/page_hierarchy.py`

#### 3. PageContentMixin (`page_content.py`)

**Purpose**: CRUD operations, text processing, page data assembly, metadata management

**Key Methods**:
- `modify_name(name)` - Updates page name (respects `auto_link_name()`)
- `modify_text(text)` - Updates page text content and processes links
- `add_page(page_class, name)` - Creates new child page
- `delete_page()` - Deletes page and all children recursively
- `get_page_data()` - Returns page metadata dictionary
- `flag_page_modification(comments)` - Updates audit trail (last_modified, username, comments)
- `set_metadata_value(key, value)` - Sets a metadata key-value pair
- `get_prepared_text()` - Returns processed text content (cached in `prepared_text` field)

**Extension Points**:
- Override `_add_page_class_information(new_page_id)` (classmethod) for class-specific setup after creation
- Override `_delete_page_class_information()` (instance method) for class-specific cleanup before deletion
- Override `get_allowed_child_classes()` to customize which child classes are allowed

**Cache Fields**: `prepared_text` (computed via `get_prepared_text()`)

**Code Reference**: `hh/page/page_content.py`

#### 4. PageImagesMixin (`page_images.py`)

**Purpose**: Image association management, ranking, copying/moving images

**Key Methods**:
- `get_images_data()` - Returns list of associated images with ranks (cached in `images` field)
- `add_image(file_path, caption)` - Adds image to page and processes upload
- `copy_images(image_ids, target_rank)` - Copies images to this page
- `move_images(image_instances, target_rank)` - Moves images from other pages
- `set_image_rank(image_id, current_rank, new_rank)` - Reorders images
- `remove_image(image_id, image_rank)` - Removes image from page

**Internal Methods**:
- `_create_image_record(caption)` - Creates image record in database
- `_add_image_to_group(image_id, rank)` - Adds image to page's image group
- `_reorder_images()` - Reorders all images to fix gaps

**Cache Fields**: `images` (computed via `get_images_data()`)

**Code Reference**: `hh/page/page_images.py`

#### 5. PageFilesMixin (`page_files.py`)

**Purpose**: File association management, ranking, copying/moving files

**Key Methods**:
- `get_files_data()` - Returns list of associated files with ranks (cached in `files` field)
- `add_file(temp_path, original_filename, description)` - Adds file to page
- `copy_files(file_ids, target_rank)` - Copies files to this page
- `move_files(file_instances, target_rank)` - Moves files from other pages
- `set_file_rank(file_id, current_rank, new_rank)` - Reorders files
- `remove_file(file_id, file_rank)` - Removes file from page

**Internal Methods**:
- `_create_file_record(...)` - Creates file record in database
- `_add_file_to_group(file_id, rank)` - Adds file to page's file group
- `_reorder_files()` - Reorders all files to fix gaps

**Cache Fields**: `files` (computed via `get_files_data()`)

**Code Reference**: `hh/page/page_files.py`

#### 6. PageDisplayMixin (`page_display.py`)

**Purpose**: Display data preparation, child grouping, badge headers

**Key Methods**:
- `show_page()` - Returns complete display data dictionary (standard output format)
- `_get_children_by_class()` - Groups children by class (cached in `children_by_class` field)
- `_get_children_for_class(child_class)` - Gets children for specific class using that class's query

**Extension Points** (all can be overridden):
- `_add_upper_content()` - Add content above main page content
- `_add_lower_content()` - Add content below main page content
- `_add_badge_headers()` - Customize badge headers
- `_get_child_row_field_type()` - Customize field type when displayed as child row

**Cache Fields**: `children_by_class` (computed via `_get_children_by_class()`)

**Code Reference**: `hh/page/page_display.py`

#### 7. PageAjaxMixin (`page_ajax.py`)

**Purpose**: AJAX-friendly JSON payload assembly for MCP backend

**Key Methods**:
- `get_page()` - Returns minimal JSON structure with available actions
  - Includes `page`, `images`, `children_by_class`
  - Adds `available_actions` for MCP backend (app actions based on user tier)

**Code Reference**: `hh/page/page_ajax.py`

#### 8. PageCacheMixin (`page_cache.py`)

**Purpose**: Cache database management for five derived fields plus main DB metadata backup

**Key Methods**:
- `_refresh_cached_page()` - Writes all five derived fields plus metadata to cache database
- `_ensure_cache_entry()` - Ensures cache entry exists in cache database
- `_flag_cache_refresh()` - Flags that cache needs refresh (called by getters)

**Cache Fields**: All five derived fields (display_name, prepared_text, children_by_class, images, files) plus metadata backup

**Code Reference**: `hh/page/page_cache.py`

#### 9. PageMaintenanceMixin (`page_maintenance.py`)

**Purpose**: Maintenance operations like regex text replacement

**Key Methods**:
- `regex_text(old_name, new_name)` - Replaces page name references in text content

**Code Reference**: `hh/page/page_maintenance.py`

### Cache System

The page system uses a two-tier cache system with automatic metadata backup, enabling full page hydration from cache database without main DB access.

#### Two-Tier Architecture

1. **Hot Cache** (`page_registry.py`): In-memory cache of Page instances for request lifetime
2. **Cache Database**: Separate database storing five derived fields plus main DB metadata backup

#### Five Derived Fields

These fields are computed on-demand and cached in the cache database:

- `display_name`: Computed display name (via `_get_display_name()`)
- `prepared_text`: Processed text content as JSON (via `get_prepared_text()`)
- `children_by_class`: Grouped children data by class as JSON (via `_get_children_by_class()`)
- `images`: Image association data as JSON (via `get_images_data()`)
- `files`: File association data as JSON (via `get_files_data()`)

#### Metadata Backup

The cache system also stores a backup of all main database fields in the `metadata` JSON column:

- `name`, `link`, `text`, `parent`, `class`, `last_modified`, `username`, `comments`, `visibility`, `displayStyle`, `viewCount`
- Plus any existing metadata fields (merged together)

This enables full page hydration from cache database without requiring main DB access (for future implementation).

#### Cache Hydration Flow

1. Page constructor loads base data from main database
2. Checks if cache exists and is fresh (`cache_built_at >= last_modified`)
3. If cache is fresh, hydrates five derived fields from cache database
4. If cache is stale or missing, fields remain empty and are computed on-demand
5. Metadata backup is stored but not yet used for hydration (future enhancement)

See `Page.__init__()` in `hh/page/page.py` for cache hydration logic.

#### Cache Refresh Flow

1. When derived fields are computed, `_flag_cache_refresh()` is called
2. During gateway commit, `refresh_stale_page_caches()` is called
3. For each flagged page, `_refresh_cached_page()` writes:
   - All five derived fields to cache database
   - Main DB fields as metadata backup
4. Updates `cache_built_at` in main database

See `PageCacheMixin._refresh_cached_page()` in `hh/page/page_cache.py` for the refresh implementation.

#### Lazy Computation Pattern

All derived fields use lazy computation - they're only computed when accessed. See `get_images_data()` in `hh/page/page_images.py` for an example of the pattern.

**Key Points**:
- Fields are computed on first access
- Computation triggers cache refresh flag
- Cache refresh happens during gateway commit
- Subsequent accesses use cached value (if fresh) or recompute (if stale)

### Page Registry

**File**: `hh/page/page_registry.py`

The page registry manages hot cache and provides page loading functions.

#### Key Functions

**`get_page(page_id: int)`**: Get page from hot cache or load from database
- Checks hot cache first
- If not found, determines page class via `_get_page_class_and_load_utils()`
- Instantiates appropriate Page subclass
- Page constructor handles main DB load and cache hydration automatically
- Stores in hot cache for future access

See `get_page()` in `hh/page/page_registry.py` for implementation.

**`find_page(link: str)`**: Find page by link
- Queries database for page with matching link
- Returns page instance via `get_page()`

See `find_page()` in `hh/page/page_registry.py` for implementation.

**`refresh_stale_page_caches()`**: Refresh cache for all flagged pages
- Called by gateway during commit process
- Iterates through hot cache and refreshes pages with `_cache_needs_refresh` flag
- Updates cache database with all five derived fields plus metadata

See `refresh_stale_page_caches()` in `hh/page/page_registry.py` for implementation.

#### Hot Cache Management

- Hot cache is a module-level dictionary: `_page_cache: Dict[int, Page]`
- Pages are stored in hot cache after first load
- Cache refresh happens during gateway commit
- No automatic expiration - pages remain in cache for request lifetime

### Page Class Registry

**File**: `hh/page/page_class_registry.py`

The page class registry manages dynamic subclass loading based on the `class` field in the database.

#### Key Functions

**`register_page_class(class_name: str)`**: Decorator to register page subclasses
- Used as `@register_page_class('class_name')` on Page subclasses
- Registers class in global registry `_page_class_registry`

See `register_page_class()` in `hh/page/page_class_registry.py` for implementation.

**`get_page_class(class_name: str)`**: Get Page subclass for a class name
- Checks hot cache first (`_page_class_registry`)
- If not found, checks cold cache (JSON file)
- If not found, rebuilds cold cache by scanning for `@register_page_class` decorators
- Returns Page class or None (falls back to base Page class)

See `get_page_class()` in `hh/page/page_class_registry.py` for implementation.

**`discover_page_classes(force_regenerate: bool)`**: Scan codebase for page classes
- Scans all Python files for `@register_page_class` decorators
- Imports modules to populate registry
- Caches results in JSON file (`hh/page/cache/page-classes.json`)

See `discover_page_classes()` in `hh/page/page_class_registry.py` for implementation.

#### Dynamic Class Loading

When `get_page(page_id)` is called:

1. Queries database for page's `class` field
2. Calls `get_page_class(class_name)` to get appropriate subclass
3. Instantiates that subclass instead of base Page class
4. Subclass inherits all mixin functionality
5. Page constructor automatically extracts metadata fields as attributes

This enables polymorphic page loading - the same `get_page()` call returns different subclasses based on database content.

---

## 2. Image Module

**Files**: `hh/image/*.py`

The image management system with CRUD operations, multi-size instance management, and display logic. Handles automatic image processing and intelligent sizing.

### Image Class

The Image class follows a similar architecture to Page:
- Uses mixins for functionality (ImageValidationMixin, ImageContentMixin, ImageInstancesMixin, ImageUsageMixin, ImageDisplayMixin, ImageCacheMixin)
- Has its own registry system (`image_registry.py`) with hot cache
- Uses cache database for derived fields (instances, pages/usage) plus metadata backup
- Follows same patterns as Page but simpler structure

#### Key Differences from Page

- **Multi-size Instances**: Images automatically generate multiple size variants (huge, large, small, tn)
- **No Hierarchy**: Images don't have parent-child relationships
- **Usage Tracking**: Images track which pages use them (via `image_groups` table)
- **File Storage**: Images stored in `/srv/images/{project}/{date}/` with date-based organization
- **Soft Deletes**: Deleted images moved to deleted subdirectory, not permanently removed

#### Registry Pattern

Similar to Page registry:
- `get_image(image_id)` - Gets from hot cache or loads from database
- `refresh_stale_image_caches()` - Refreshes cache during gateway commit
- Hot cache: `_image_cache: Dict[int, Image]`

#### Cache System

Images cache two derived fields plus metadata:
- `instances`: Multi-size image instance data (JSON)
- `pages`: Usage data - which pages use this image (JSON)
- `metadata`: Backup of main DB fields (caption, username, uploaded, last_modified, comments, visibility, viewCount)

See `ImageCacheMixin._refresh_cached_image()` in `hh/image/image_cache.py` for cache refresh implementation.

---

## 3. File Module

**Files**: `hh/file/*.py`

The file management system with CRUD operations and display logic. Follows the same patterns as Image but even simpler.

### File Class

The File class follows the same architecture as Image and Page:
- Uses mixins (FileContentMixin, FileCacheMixin)
- Has registry system with hot cache
- Uses cache database for derived fields plus metadata backup
- Simplest of the three (no multi-size processing, no hierarchy)

#### Key Differences from Image

- **No Instances**: Files are stored as-is, no size variants
- **No Hierarchy**: Files don't have parent-child relationships
- **Usage Tracking**: Files track which pages use them (via `file_groups` table)
- **File Storage**: Files stored in `/srv/files/{project}/{date}/` with date-based organization
- **Soft Deletes**: Deleted files moved to deleted subdirectory

#### Registry Pattern

Same as Image and Page:
- `get_file(file_id)` - Gets from hot cache or loads from database
- `refresh_stale_file_caches()` - Refreshes cache during gateway commit (called by gateway)
- Hot cache managed in `file_registry.py`

#### Cache System

Files cache one derived field plus metadata:
- `pages`: Usage data - which pages use this file (JSON)
- `metadata`: Backup of main DB fields (file_name, file_path, description, mime_type, size_bytes, username, uploaded, last_modified, comments, visibility)

See `FileCacheMixin._refresh_cached_file()` in `hh/file/file_cache.py` for cache refresh implementation.

---

## 4. Text Processor Module

**Files**: `hh/tp/*.py` and `hh/tp/*.ini`

The custom markup parsing system for page content. Implements decorator-based processing with configurable decorator registry.

**Note**: This module is documented separately. The Page system integrates with TextProcessor via `get_prepared_text()`, which processes page text content and caches the result in the `prepared_text` field.

**Key Integration Points**:
- `PageContentMixin.get_prepared_text()` - Calls `TextProcessor.preprocess()` to process text
- `PageContentMixin.modify_text()` - Validates text with TextProcessor and updates links table
- Processed text cached in `prepared_text` field (part of the five derived fields)

---

## Integration with Other Systems

### With Gateway (see gateway.md)
- Actions create Page/Image/File instances and call mixin methods
- Actions return JSON via `gateway.response.set_action_response()`
- Backends receive Page/Image/File JSON data for formatting
- Cache refresh happens during gateway commit via `refresh_stale_page_caches()`, `refresh_stale_image_caches()`, `refresh_stale_file_caches()`

### With Registry (see registry.md)
- Page/Image/File actions use `@register_action` decorator
- Backends use appropriate `@register_parser`/`@register_http`/`@register_mcp` decorators
- Handlers auto-discovered and registered

### With Render System (see render.md)
- Backends use render functions to format Page/Image/File data
- Page/Image/File display data structure compatible with render system
- `FieldConfig` used for table formatting
- `render_show_page()` handles page display rendering for parser/HTTP backends

### With MCP Backend (see mcp.md)
- Page operations exposed as MCP tools via `mcp_utils.py`
- Tier-based access control via `@register_mcp_tool` decorators
- `PageAjaxMixin.get_page()` provides lightweight JSON for MCP responses
- App actions layer provides web UI integration

### Database Access Pattern
- All modules use `gateway.conn` methods directly
- Page/Image/File mixins call `gateway.conn.read()`, `gateway.conn.create()`, `gateway.conn.update()`, `gateway.conn.delete()`
- Cache operations use `gateway.conn.read_cache()`, `gateway.conn.create_cache()`, `gateway.conn.update_cache()`
- Tier-based credentials loaded from `~/.project.cnf` files
