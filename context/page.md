# Page System Architecture Documentation

This document covers the core business logic modules for page, image, and text processing in the Python Gateway-based system. The Page system is the **extensible infrastructure** upon which all content management is built. It provides a hierarchical content management system with CRUD operations, display logic, and content processing, designed from the ground up to be extended through derived classes.

For Gateway, Registry, Render, and other infrastructure details, see the respective documentation files.

## Table of Contents

1. [Page Module](#1-page-module)
   - [Core Architecture](#core-architecture)
   - [The Five Validation Functions](#the-five-validation-functions)
   - [Extensibility System](#extensibility-system)
   - [CRUD Operations](#crud-operations)
   - [Cache System](#cache-system)
   - [Page Registry](#page-registry)
   - [Page Class Registry](#page-class-registry)
2. [Image Module](#2-image-module)
3. [File Module](#3-file-module)
4. [Audio Module](#4-audio-module)
5. [Video Module](#5-video-module)
6. [Generalized Media Operations](#6-generalized-media-operations)
7. [Text Processor Module](#7-text-processor-module)

## Agent Quick Reference

- **Core Modules**: `page/` (hierarchical content), `image/` (image management), `file/` (file management), `audio/` (audio management), `video/` (video management), `tp/` (markup parsing)
- **Architecture**: Page class provides comprehensive functionality with direct database access via `self.gateway.conn`
- **Extensibility**: Base Page class designed for inheritance; derived classes override validation functions, hooks, and display methods
- **Cache System**: Five derived fields (display_name, prepared_text, children_by_class, images, files) plus main DB metadata cached in separate cache database. Audio and video also cached with instances and pages/usage data.
- **Page Registry**: Hot cache system with automatic cache refresh during gateway commit
- **Page Class Registry**: Dynamic subclass loading based on page class field
- **Markup Language**: `[[page_links]]`, `{{image_embeds}}`, decorator-based processing
- **Page Hierarchy**: Parent-child relationships with automatic breadcrumb generation
- **Image Instances**: Automatic multi-size generation and management (huge, large, small, tn)
- **Audio/Video Instances**: Multi-quality tier transcoding (full, standard, high, medium, low) via background maintenance jobs
- **Generalized Media Operations**: Unified copy/move/remove/set_rank methods work across all media types (image, file, audio, video)
- **Text Processing**: Decorator-based parsing with configurable decorator registry

## Agent Training Notes

### Module Integration
- **Page Objects**: Actions create Page instances via `get_page(page_id)` from page registry
- **Image Objects**: Actions create Image instances for media operations
- **File Objects**: Actions create File instances for file operations
- **Audio Objects**: Actions create Audio instances for audio operations
- **Video Objects**: Actions create Video instances for video operations
- **Text Processing**: Page content parsed through TextProcessor with decorator registry
- **Page Methods**: Pages provide comprehensive methods for all operations
- **Display Methods**: Call `show_page()` for formatted output data

### Common Usage Patterns
- **Page Creation**: `get_page(page_id)` loads from hot cache or database
- **Image Management**: `Image(image_id)` handles multi-size instances automatically
- **File Management**: `File(file_id)` handles file storage and usage tracking
- **Audio Management**: `Audio(audio_id)` handles audio transcoding and quality tiers
- **Video Management**: `Video(video_id)` handles video transcoding and quality tiers
- **Media Operations**: Use generalized methods (`copy_media_items()`, `move_media_items()`, `remove_media_item()`, `set_media_rank()`) with `media_type` parameter
- **Content Parsing**: TextProcessor decorators parse custom markup syntax
- **Data Retrieval**: All modules load from database via `gateway.conn` methods

---

## 1. Page Module

**Files**: `hh/page/*.py`

The hierarchical page management system with CRUD operations, display logic, and content processing. **The Page system is designed as extensible infrastructure** - the base `Page` class provides core functionality, while derived classes extend it for specific content types (source code files, work pages, etc.).

### Core Architecture

The Page class provides comprehensive functionality organized into focused areas, with a modular architecture that can be extended through inheritance. All Page methods access the database directly through `self.gateway.conn`.

#### Page Class Structure

The Page class is defined in `hh/page/page.py`. See the class definition for the complete method list.

#### Metadata Extraction

The Page constructor automatically extracts metadata fields as object attributes, enabling derived classes to store custom data in the metadata JSON field and access it directly. See `Page.__init__()` in `hh/page/page.py` (around lines 115-127) for the extraction logic.

**Key Points**:
- Metadata fields are automatically extracted as `self.attribute_name`
- Existing Page attributes are protected (metadata won't overwrite them)
- Derived classes can store custom fields in metadata and access them directly
- Example: `SourceCodeFile` stores `file_path` and `language` in metadata, accessible as `self.file_path` and `self.language`

#### Database Access Pattern

All Page methods access the database directly through `self.gateway.conn`. See any Page method (e.g., `modify_name()`) for examples.

**Key Points**:
- All methods use `self.gateway.conn` directly
- No decorators or wrapper methods needed
- Connection is automatically managed by gateway
- Methods work within existing transactions

### The Five Validation Functions

The Page system provides **five validation functions** that control page behavior and hierarchy constraints. These are the primary extension points for derived classes to customize validation rules.

All five functions are defined in the Page class and can be overridden by derived classes:

#### 1. `allow_null_names()` - Class Method

**Signature**: `@classmethod def allow_null_names(cls) -> bool`

**Default**: Returns `False` (names required)

**Purpose**: Determines if pages of this class can have `NULL` names in the database.

**When to Override**: 
- Set to `True` for classes that don't require names (e.g., `SourceCodeFile`, `WorkDocket`)
- Set to `False` for classes that must have names (e.g., base `Page`)

**Example Override**: See `SourceCodeFile.allow_null_names()` in `hh/source_code_file/source_code_file.py`

#### 2. `allow_duplicate_names()` - Class Method

**Signature**: `@classmethod def allow_duplicate_names(cls) -> bool`

**Default**: Returns `True` (duplicates allowed)

**Purpose**: Determines if multiple pages of this class can have the same name under the same parent.

**When to Override**:
- Set to `False` to enforce unique names within a parent (rare)
- Keep `True` for most use cases

**Example Override**: See `SourceCodeFile.allow_duplicate_names()` in `hh/source_code_file/source_code_file.py`

#### 3. `auto_link_name()` - Class Method

**Signature**: `@classmethod def auto_link_name(cls) -> bool`

**Default**: Returns `True` (auto-link enabled)

**Purpose**: Determines if the `link` field should automatically be set to match the `name` field when a page is created or renamed.

**When to Override**:
- Set to `False` for classes that manage links manually (e.g., `SourceCodeFile`, `WorkDocket`)
- Keep `True` for simple pages where name and link should match

**Example Override**: See `SourceCodeFile.auto_link_name()` in `hh/source_code_file/source_code_file.py`

#### 4. `allow_class_inside()` - Instance Method

**Signature**: `def allow_class_inside(self, target_class: str) -> bool`

**Default**: Returns `True` (can contain any class)

**Purpose**: Determines if **this page instance** can contain child pages of the specified `target_class`.

**When to Override**:
- Restrict which child classes are allowed under this page type
- Example: Work dockets might only allow "ask" children

**Example Override**: See `SourceCodeFile.allow_class_inside()` in `hh/source_code_file/source_code_file.py`

#### 5. `allow_inside_of()` - Class Method

**Signature**: `@classmethod def allow_inside_of(cls, parent_class: str) -> bool`

**Default**: Returns `True` (can be inside any class)

**Purpose**: Determines if pages of **this class** can be created inside pages of the specified `parent_class`.

**When to Override**:
- Enforce hierarchy constraints (e.g., "asks can only be inside work dockets")
- Prevent abstract classes from being instantiated directly

**Example Override** (Abstract Class): See `WorkPage.allow_inside_of()` in `hh/work/work_page.py` - prevents abstract class from being instantiated directly.

**Example Override** (Hierarchy Constraint): See `WorkDocket.allow_inside_of()` in `hh/work_docket/work_docket.py`

#### Validation Function Usage

These functions are called during:
- **Page Creation** (`add_page()`): Checks `allow_null_names()`, `allow_duplicate_names()`, `allow_class_inside()`, `allow_inside_of()`
- **Name Modification** (`modify_name()`): Checks `allow_null_names()`, `allow_duplicate_names()`, `auto_link_name()`
- **Move Operations** (`move_page()`): Checks `allow_class_inside()` and `allow_inside_of()`

See `Page.validate_name()` in `hh/page/page.py` for the full implementation that uses these functions.

### Extensibility System

The Page system is designed for extension through inheritance. Derived classes can override validation functions, hooks, and display methods to customize behavior.

#### Creating Derived Classes

Derived classes extend `Page` (or intermediate abstract classes):

**Simple Derived Class Example**: See `SourceCodeFile` class in `hh/source_code_file/source_code_file.py` - extends Page directly with custom validation and content methods.

**Abstract Intermediate Class Example**: See `WorkPage` class in `hh/work/work_page.py` - abstract base class that extends Page and provides shared functionality (status, meta, sort_order) for work entities.

**Concrete Derived Class Example**: See `WorkDocket` class in `hh/work_docket/work_docket.py` - extends WorkPage (which extends Page) with work docket-specific validation and content methods.

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

See `Page._add_page_class_information()` and `_delete_page_class_information()` in `hh/page/page.py` for the base implementations.

##### Display Hooks

**`_get_display_name()`** - Instance Method
- Override to customize how page names are displayed
- Default: Returns `self.name` or `f"Page {self.id}"`
- Example: See `SourceCodeFile._get_display_name()` in `hh/source_code_file/source_code_file.py` for an override that extracts filename from `file_path` when name is null

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
- See `Page._add_badge_headers()` in `hh/page/page.py` for base implementation

**`_get_child_row_field_type()`** - Instance Method
- Override to customize the field type/icon shown when this page appears as a child in tables
- Returns string field type (used for rendering icons/labels)
- Default: Returns `'page'`
- Example: See `WorkDocket._get_child_row_field_type()` in `hh/work_docket/work_docket.py` for status-based field types

##### Hierarchy Hooks

**`_get_children_query(parent_id: int)`** - Static Method
- Override to customize which children are returned and how they're ordered
- Returns tuple of `(query_string, params_list)`
- Default: Returns only 'page' class children, sorted by name
- Example: See `WorkDocket._get_children_query()` in `hh/work_docket/work_docket.py` for custom ordering by metadata sort_order

**`getChildrenOf(parent_id: int, view_type: str = 'tile')`** - Static Method
- Override to customize default view_type and class-specific child retrieval behavior
- Called as static method on child class (e.g., `SourceCodeFile.getChildrenOf(parent_id)`)
- Matches legacy `getChildrenOf()` pattern where each class handles its own children
- Default: `view_type='tile'` in base class, can be overridden (e.g., `SourceCodeFile` defaults to `'table'`)
- Uses the class's own `_get_children_query()` to get children of that specific class
- Example: See `SourceCodeFile.getChildrenOf()` in `hh/source_code_file/source_code_file.py` for class-specific override

**`_copy_page_class_information(new_page_id: int)`** - Instance Method
- Override to customize what happens when a page is copied
- Called during `copy_page()` operation
- Default: No-op

#### Custom Metadata Namespaces

Derived classes can use the metadata JSON field to store custom data. The Page constructor automatically extracts metadata fields as attributes, so derived classes can access them directly:

**Example**: `WorkPage` stores `status`, `meta`, and `sort_order` in metadata:
- These are automatically available as `self.status`, `self.meta`, `self.sort_order`
- Derived classes like `WorkDocket` inherit this behavior
- The `WorkPage` class provides methods to modify these fields

### CRUD Operations

Page CRUD operations follow a consistent pattern across all actions. Most actions use `show_page()` as their standard output format.

#### Action Pattern

All page actions follow this structure:

1. **Registration**: Use `@register_action` and `@register_command` decorators
2. **Argument Validation**: Check required arguments via `gateway.is_set()` and `gateway.get_arg()`
3. **Page Loading**: Load page via `get_page(page_id)` from registry
4. **Operation**: Call method on page instance (e.g., `page.modify_name()`, `page.add_page()`)
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

See `Page.show_page()` in `hh/page/page.py` for the full implementation. For MCP backend, it returns a lightweight payload without badge headers and extra content.

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

See `Page._refresh_cached_page()` in `hh/page/page.py` for the refresh implementation.

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
4. Subclass inherits all Page functionality
5. Page constructor automatically extracts metadata fields as attributes

This enables polymorphic page loading - the same `get_page()` call returns different subclasses based on database content.

---

## 2. Image Module

**Files**: `hh/image/*.py`

The image management system with CRUD operations, multi-size instance management, and display logic. Handles automatic image processing and intelligent sizing.

### Image Class

The Image class follows a similar architecture to Page:
- Provides comprehensive functionality organized into focused areas
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

See `Image._refresh_cached_image()` in `hh/image/image.py` for cache refresh implementation.

---

## 3. File Module

**Files**: `hh/file/*.py`

The file management system with CRUD operations and display logic. Follows the same patterns as Image but simpler (no multi-size processing).

### File Class

The File class follows the same architecture as Image and Page:
- Provides comprehensive functionality organized into focused areas
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

See `File._refresh_cached_file()` in `hh/file/file.py` for cache refresh implementation.

---

## 4. Audio Module

**Files**: `hh/audio/*.py`

The audio management system with CRUD operations, transcoding support, and display logic. Follows the same patterns as Image and File but with audio-specific processing.

### Audio Class

The Audio class follows the same architecture as Image and Page:
- Provides comprehensive functionality organized into focused areas
- Has registry system (`audio_registry.py`) with hot cache
- Uses cache database for derived fields (instances, pages/usage) plus metadata backup
- Supports multiple quality tiers (full, standard, high, medium, low) via transcoding

#### Key Differences from Image

- **Audio Instances**: Audio files support multiple quality tiers (full original, standard, high, medium, low) in AAC format
- **Transcoding**: Background maintenance job (`audio_transcode`) creates all quality tiers automatically
- **Metadata Extraction**: Uses `mutagen` library for audio file validation and metadata extraction (duration, bitrate, channels, sample_rate)
- **No Hierarchy**: Audio files don't have parent-child relationships
- **Usage Tracking**: Audio tracks which pages use them (via `audio_groups` table)
- **File Storage**: Audio stored in `/srv/audio/{project}/{date}/` with date-based organization
- **Soft Deletes**: Deleted audio moved to deleted subdirectory

#### Registry Pattern

Same as Image and File:
- `get_audio(audio_id)` - Gets from hot cache or loads from database
- `refresh_stale_audio_caches()` - Refreshes cache during gateway commit
- Hot cache: `_audio_cache: Dict[int, Audio]`

#### Cache System

Audio caches two derived fields plus metadata:
- `instances`: Multi-quality audio instance data (JSON)
- `pages`: Usage data - which pages use this audio (JSON)
- `metadata`: Backup of main DB fields (caption, username, uploaded, last_modified, comments, visibility, viewCount)

See `Audio._refresh_cached_audio()` in `hh/audio/audio.py` for cache refresh implementation.

---

## 5. Video Module

**Files**: `hh/video/*.py`

The video management system with CRUD operations, transcoding support, and display logic. Follows the same patterns as Audio but with video-specific processing.

### Video Class

The Video class follows the same architecture as Audio and Image:
- Provides comprehensive functionality organized into focused areas
- Has registry system (`video_registry.py`) with hot cache
- Uses cache database for derived fields (instances, pages/usage) plus metadata backup
- Supports multiple quality tiers (full, standard, high, medium, low) via transcoding

#### Key Differences from Audio

- **Video Instances**: Video files support multiple quality tiers (full original, standard, high, medium, low) in MP4 (H.264) format
- **Transcoding**: Background maintenance job (`video_transcode`) creates all quality tiers automatically
- **Metadata Extraction**: Uses `ffprobe` for video file validation and metadata extraction (width, height, duration, bitrate)
- **No Hierarchy**: Video files don't have parent-child relationships
- **Usage Tracking**: Video tracks which pages use them (via `video_groups` table)
- **File Storage**: Video stored in `/srv/video/{project}/{date}/` with date-based organization
- **Soft Deletes**: Deleted video moved to deleted subdirectory

#### Registry Pattern

Same as Audio and Image:
- `get_video(video_id)` - Gets from hot cache or loads from database
- `refresh_stale_video_caches()` - Refreshes cache during gateway commit
- Hot cache: `_video_cache: Dict[int, Video]`

#### Cache System

Video caches two derived fields plus metadata:
- `instances`: Multi-quality video instance data (JSON)
- `pages`: Usage data - which pages use this video (JSON)
- `metadata`: Backup of main DB fields (caption, username, uploaded, last_modified, comments, visibility, viewCount)

See `Video._refresh_cached_video()` in `hh/video/video.py` for cache refresh implementation.

---

## 6. Generalized Media Operations

The Page class provides unified media operations that work across all media types (images, files, audio, video) through a `media_type` parameter. This eliminates code duplication and ensures consistent behavior.

### Generalized Methods

**`copy_media_items(media_type: str, item_ids: List[int], target_rank: Optional[int] = None) -> bool`**
- Copies media items to the current page
- Supports all media types: `"image"`, `"file"`, `"audio"`, `"video"`
- Uses dynamic helper methods to resolve table names, field names, and methods based on `media_type`
- Returns `True` on success, `False` on failure

**`move_media_items(media_type: str, item_instances: List[Dict[str, int]], target_rank: Optional[int] = None) -> bool`**
- Moves media items from source pages to the current page
- Handles removal from source page and addition to target page
- Reorders affected pages automatically
- `item_instances` format: `[{"item_id": 123, "source_page_id": 456, "source_rank": 1}, ...]`

**`remove_media_item(media_type: str, item_id: int, item_rank: int) -> bool`**
- Removes a media item from the current page
- Reorders the page to eliminate gaps
- Conditionally deletes the underlying media object if no longer used (soft delete)

**`set_media_rank(media_type: str, item_id: int, current_rank: int, new_rank: int) -> bool`**
- Sets the rank of a media item within a page's media group
- Implements hybrid approach: efficient "delete-and-reflow" for single moves, with final verification to ensure sequential ranks and no gaps
- Returns `True` on success, `False` on failure

### Dynamic Helper Methods

The Page class includes helper methods that dynamically resolve database entities and methods based on `media_type`:

- `_get_media_table_name(media_type: str)` - Returns table name (e.g., `"image_groups"`, `"audio_groups"`)
- `_get_media_id_field(media_type: str)` - Returns ID field name (e.g., `"image_id"`, `"audio_id"`)
- `_get_media_rank_field(media_type: str)` - Returns rank field name (e.g., `"image_rank"`, `"audio_rank"`)
- `_get_media_data_method(media_type: str)` - Returns data retrieval method (e.g., `get_images_data`, `get_audio_data`)
- `_get_add_to_group_method(media_type: str)` - Returns add method (e.g., `_add_image_to_group`, `_add_audio_to_group`)
- `_get_reorder_method(media_type: str)` - Returns reorder method (e.g., `_reorder_images`, `_reorder_audio`)
- `_validate_media_type(media_type: str)` - Validates media type is supported

### Page Integration

All media types are integrated into pages via group tables:
- `image_groups` - Links images to pages with ranks
- `file_groups` - Links files to pages with ranks
- `audio_groups` - Links audio to pages with ranks
- `video_groups` - Links video to pages with ranks

The `show_page()` method includes all media types in its response:
- `images`: Image association data
- `files`: File association data
- `audio`: Audio association data
- `video`: Video association data

### Action Scripts

Individual action scripts (e.g., `copy_images.py`, `copy_audio.py`, `move_video.py`) call the generalized methods directly with the appropriate `media_type` parameter. This ensures consistent behavior across all media types while maintaining clear, dedicated action handlers.

---

## 8. Text Processor Module

**Files**: `hh/tp/*.py` and `hh/tp/*.ini`

The custom markup parsing system for page content. Implements decorator-based processing with configurable decorator registry.

**Note**: This module is documented separately. The Page system integrates with TextProcessor via `get_prepared_text()`, which processes page text content and caches the result in the `prepared_text` field.

**Key Integration Points**:
- `Page.get_prepared_text()` - Calls `TextProcessor.preprocess()` to process text
- `Page.modify_text()` - Validates text with TextProcessor and updates links table
- Processed text cached in `prepared_text` field (part of the five derived fields)

---

## Integration with Other Systems

### With Gateway (see gateway.md)
- Actions create Page/Image/File/Audio/Video instances and call their methods
- Actions return JSON via `gateway.response.set_action_response()`
- Backends receive Page/Image/File/Audio/Video JSON data for formatting
- Cache refresh happens during gateway commit via `refresh_stale_page_caches()`, `refresh_stale_image_caches()`, `refresh_stale_file_caches()`, `refresh_stale_audio_caches()`, `refresh_stale_video_caches()`

### With Registry (see registry.md)
- Page/Image/File/Audio/Video actions use `@register_action` decorator
- Backends use appropriate `@register_parser`/`@register_http`/`@register_mcp` decorators
- Handlers auto-discovered and registered

### With Render System (see render.md)
- Backends use render functions to format Page/Image/File/Audio/Video data
- Page/Image/File/Audio/Video display data structure compatible with render system
- `FieldConfig` used for table formatting
- `render_show_page()` handles page display rendering for parser/HTTP backends
- Tile rendering system (`TileGroup`, `ImageGroup`, `PageGroup`) provides alternative grid layout for images and children
- View type support (`view_type` parameter) enables dynamic switching between table and tile views
- Wrapper ID support in `render_block()` enables DOM targeting for view toggle system
- Audio and video sections support table view (tile view not yet implemented)

### With MCP Backend (see mcp.md)
- Page operations exposed as MCP tools via `mcp_utils.py`
- Tier-based access control via `@register_mcp_tool` decorators
- `Page.get_page()` provides lightweight JSON for MCP responses
- App actions layer provides web UI integration

### Database Access Pattern
- All modules use `gateway.conn` methods directly
- Page/Image/File/Audio/Video classes call `gateway.conn.read()`, `gateway.conn.create()`, `gateway.conn.update()`, `gateway.conn.delete()`
- Cache operations use `gateway.conn.read_cache()`, `gateway.conn.create_cache()`, `gateway.conn.update_cache()`
- Tier-based credentials loaded from `~/.project.cnf` files

### Media Operations Consistency

All media types (images, files, audio, video) support consistent operations:
- **Copy**: `copy_media_items()` - Copy items to a target page
- **Move**: `move_media_items()` - Move items from source to target page
- **Remove**: `remove_media_item()` - Remove item from page (with soft delete if unused)
- **Set Rank**: `set_media_rank()` - Reorder items within a page's media group
- **Add**: Type-specific methods (`add_image()`, `add_file()`, `add_audio()`, `add_video()`) handle file processing and group association

All operations are available via both singular and plural action scripts (e.g., `copy_image.py` and `copy_images.py`, `move_audio.py` and `move_audios.py`), ensuring consistent API across all media types.
