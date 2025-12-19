# Multimedia System Architecture Plan

This document outlines the complete plan for extending the Henhouse system to support multimedia content types (audio and video) and refining the existing file download system. This builds on the existing image and file infrastructure, following the same architectural patterns.

## Current State

### Images System
- **Status**: Fully operational
- **Database**: `images` table, `image_groups` table, `image_instances` table
- **Storage**: `/srv/images/{project_name}/` with date-based organization
- **Routes**: `/img/<id>` shows image page via `show-image` action, `/img/<id>/download` for direct download
- **Direct Serving**: Images currently served directly via NGINX `/srv/images/` location block
- **Integration**: Fully integrated with pages via `image_groups`, displayed in `show_page` responses
- **TypeScript**: Image viewer overlay exists (`image-viewer.ts`), image group sorter exists
- **Cache**: Two-tier cache system (hot cache + cache database)

### Files System
- **Status**: Fully operational
- **Database**: `files` table, `file_groups` table
- **Storage**: `/srv/files/{project_name}/` with date-based organization
- **Routes**: `/file/<id>` shows file page via `show-file` action, `/file/<id>/download` for direct download
- **Direct Serving**: Files served via Flask routes (NGINX direct serving disabled)
- **Integration**: Fully integrated with pages via `file_groups`, displayed in `show_page` responses
- **TypeScript**: No file viewer overlay yet
- **Cache**: Two-tier cache system (hot cache + cache database)
- **Actions**: `show_file` action and backend handlers implemented (`hh/file/show_file.py`, `hh/file/render_show_file.py`)
- **Page Operations**: All operations implemented (`copy_file.py`, `copy_files.py`, `move_file.py`, `move_files.py`, `remove_file.py`, `set_file_rank.py`, `add_file.py`, `add_files.py`) - matches image/audio/video pattern

### Audio System
- **Status**: Python backend complete (including transcoding), TypeScript pending
- **Database**: `audio` table, `audio_groups` table, `audio_instances` table (main + cache)
- **Storage**: `/srv/audio/{project_name}/` with date-based organization
- **Routes**: `/audio/<id>` shows audio page via `show-audio` action, `/audio/<id>/stream` for streaming playback
- **Direct Serving**: Audio served via Flask routes
- **Integration**: Fully integrated with pages via `audio_groups` (Python backend complete)
- **TypeScript**: Not yet implemented (viewer, sorter, actions, upload handler)
- **Cache**: Two-tier cache system (hot cache + cache database)
- **Actions**: All Python actions implemented (show, add, upload, modify caption, delete, set visibility)
- **Processing**: File validation via `mutagen`, metadata extraction, transcoding to AAC format (all quality tiers)
- **Maintenance**: Background transcoding job (`audio_transcode`) creates all quality tiers automatically

### Video System
- **Status**: Python backend complete (including transcoding), TypeScript pending
- **Database**: `video` table, `video_groups` table, `video_instances` table (main + cache)
- **Storage**: `/srv/video/{project_name}/` with date-based organization
- **Routes**: `/video/<id>` shows video page via `show-video` action, `/video/<id>/stream` for streaming playback
- **Direct Serving**: Video served via Flask routes
- **Integration**: Fully integrated with pages via `video_groups` (Python backend complete)
- **TypeScript**: Not yet implemented (viewer, sorter, actions, upload handler)
- **Cache**: Two-tier cache system (hot cache + cache database)
- **Actions**: All Python actions implemented (show, add, upload, modify caption, delete, set visibility)
- **Processing**: File validation via `ffprobe`, metadata extraction, transcoding to MP4 (H.264) format (all quality tiers)
- **Maintenance**: Background transcoding job (`video_transcode`) creates all quality tiers automatically

## Goals

1. **Refine File System**: ✅ COMPLETE - Add `show_file` action, change `/file/<id>` to show page, add `/file/<id>/download` route
2. **Add Image Download Route**: ✅ COMPLETE - Add `/img/<id>/download` route to match file pattern
3. **Implement Audio System**: ✅ COMPLETE (Python backend) - Complete audio support following image/file patterns
4. **Implement Video System**: ✅ COMPLETE (Python backend) - Complete video support following image/file patterns
5. **Disable Direct NGINX Serving**: ✅ COMPLETE - Remove direct file serving from NGINX, route through Flask
6. **Generalize Media Operations**: ✅ COMPLETE - Create unified copy/move/remove/set_rank methods for all media types
7. **Complete File Operations**: ✅ COMPLETE - Add missing file operations (copy_file, move_file, add_file, add_files) to match pattern

## File System Refinement

### 1. Create `show_file` Action

**File**: `hh/file/show_file.py`

- Action handler: `@register_action('show_file')` and `@register_command('show_file')`
- Loads file via `get_file(file_id)`
- Calls `file.show_file()` method (to be added to File class)
- Returns structured data via `gateway.response.set_action_response(success_payload(data))`

### 2. Add `show_file()` Method to File Class

**File**: `hh/file/file.py`

- Method: `def show_file(self) -> Dict[str, Any]`
- Returns: `{"file": file_data, "usage": usage_data}`
- Similar structure to `Image.show_image()` but simpler (no instances)
- Usage data: which pages use this file (from `file_groups`)

### 3. Create Backend Handlers for `show_file`

**File**: `hh/file/render_show_file.py`

- Parser backend: `@register_parser('show_file')`
- HTTP backend: `@register_http('show_file')`
- Renders file information similar to `render_show_image.py`
- Displays file metadata, usage information, download link

### 4. Update Flask Routes ✅ COMPLETE

**Status**: Flask routes have been implemented in `hh/deploy/flask/app.py`

**File**: `hh/deploy/flask/app.py`

**Changed `/file/<id>` route:**
- Now shows file page via `show-file --id {file_id}` (like `/img/<id>`)
- Routes through `http_client.py` subprocess
- Returns JSON or HTML based on response content

**Added `/file/<id>/download` route:**
- Route for actual file download
- Uses download backend via `download_client.py` with `get_file_info` command
- Serves file with `Content-Disposition` header
- All file downloads go through this route for gated access

**Added `/img/<id>/download` route:**
- Route for direct image download
- Uses download backend via `download_client.py` with `get_image_info` command
- Serves full-size image file with `Content-Disposition` header
- Enables gated access to full-size images (not embedded in page source)

**Added `/audio/<id>` route:**
- Shows audio page via `show-audio --id {audio_id}`
- Routes through `http_client.py` subprocess
- Same pattern as `/img/<id>` and `/file/<id>` routes

**Added `/audio/<id>/stream` route:**
- Streams audio file for playback
- Uses download backend via `download_client.py` with `get_audio_info` command
- Serves audio file with proper MIME type
- Supports HTTP range requests for seeking (via Flask's `send_file()` with `conditional=True`)

**Added `/video/<id>` route:**
- Shows video page via `show-video --id {video_id}`
- Routes through `http_client.py` subprocess
- Same pattern as other media routes

**Added `/video/<id>/stream` route:**
- Streams video file for playback
- Uses download backend via `download_client.py` with `get_video_info` command
- Serves video file with proper MIME type
- Supports HTTP range requests for seeking (via Flask's `send_file()` with `conditional=True`)

**Implementation Notes:**
- All routes follow consistent patterns for error handling, logging, and concurrency control
- Show routes use `http_client.py` with appropriate `show-*` actions
- Download/stream routes use `download_client.py` to get metadata, then serve files with `send_file()`
- Stream routes use `conditional=True` for HTTP range request support (enables seeking)
- All routes include proper semaphore-based concurrency control and timeout handling

### 5. Disable NGINX Direct File Serving

**File**: `hh/deploy/http/nginx_whitelist.py`

- Remove `/srv/files/` location block from `_generate_location_blocks()` function
- Keep `/srv/images/` location block for now (can be disabled later if desired)
- After change: Run `http_deploy` or `deploy-ssl` to regenerate NGINX configs
- Reload NGINX: `sudo nginx -t && sudo nginx -s reload`

## Audio System Implementation

### 1. Database Schema ✅ COMPLETE

**Status**: Database schema has been implemented in `hh/deploy/db/init.sql` and `hh/deploy/db/init_cache.sql`

**Main Database Tables** (`hh/deploy/db/init.sql`):

```sql
CREATE TABLE IF NOT EXISTS `audio` (
  `id` int NOT NULL AUTO_INCREMENT,
  `caption` varchar(255) DEFAULT NULL,
  `username` varchar(255) NOT NULL,
  `uploaded` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `viewCount` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `username` (`username`),
  KEY `uploaded` (`uploaded`),
  KEY `visibility` (`visibility`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audio_groups` (
  `page_id` int NOT NULL,
  `audio_id` int NOT NULL,
  `audio_rank` int NOT NULL,
  PRIMARY KEY (`page_id`, `audio_id`, `audio_rank`),
  KEY `idx_page_rank` (`page_id`, `audio_rank`),
  KEY `idx_audio` (`audio_id`),
  CONSTRAINT `fk_audio_groups_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_audio_groups_audio` FOREIGN KEY (`audio_id`) REFERENCES `audio` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audio_instances` (
  `audio_id` int NOT NULL,
  `instance_type` varchar(32) NOT NULL,  -- 'full', 'preview' (10-second clip)
  `file_path` varchar(1024) NOT NULL,
  `mime_type` varchar(128) NOT NULL,
  `size_bytes` bigint NOT NULL,
  `duration_seconds` decimal(10,2) DEFAULT NULL,
  `bitrate` int DEFAULT NULL,
  KEY `idx_audio_id` (`audio_id`),
  CONSTRAINT `fk_audio_instances_audio` FOREIGN KEY (`audio_id`) REFERENCES `audio` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Cache Database Tables** (`hh/deploy/db/init_cache.sql`):

```sql
CREATE TABLE IF NOT EXISTS `audio` (
  `id` int NOT NULL,
  `instances` json DEFAULT NULL,
  `pages` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Actual Implementation Notes:**
- Tables match the `images` and `files` pattern exactly
- Main database uses relational structure (no JSON metadata in main tables)
- Cache database uses JSON for derived fields (`instances`, `pages`, `metadata`)
- Foreign key constraints with CASCADE deletes
- Indexes on `username`, `uploaded`, `visibility` for common queries
- `audio_instances` table includes: `audio_id`, `instance_type`, `file_path`, `mime_type`, `size_bytes`, `duration_seconds`, `bitrate`
- `audio_groups` table uses composite primary key: `(page_id, audio_id, audio_rank)`

### 2. Module Structure

Create `hh/audio/` directory with:

- **`audio.py`**: Audio class (similar to `Image` class)
  - Methods: `__init__()`, `show_audio()`, `get_audio_data()`, `get_instances()`, `get_instances_data()`, `get_usage_data()`, `_refresh_cached_audio()`, CRUD operations
  - Cache hydration from cache database
  - Lazy computation of derived fields
  - Instance management (full audio, preview clip)
  - `process_upload()` method: mimics image processing but simplified
    - MIME type validation (`audio/*`)
    - File validation using `mutagen` library (if available)
    - Creates date-based directory structure
    - Saves full-size version (original file)
    - Extracts metadata (duration, bitrate) using `mutagen`
    - Creates single instance entry in `audio_instances` table (type='full')
    - Enqueues maintenance job (`audio_transcode`) for background transcoding
    - Infrastructure ready for quality tier processing

- **`audio_registry.py`**: Hot cache system
  - `get_audio(audio_id)` function
  - `refresh_stale_audio_caches()` function
  - Module-level `_audio_cache: Dict[int, Audio]`

- **`show_audio.py`**: Action handler
  - `@register_action('show_audio')` and `@register_command('show_audio')`
  - Loads audio, calls `audio.show_audio()`, sets action response

- **`render_show_audio.py`**: Backend handlers
  - `@register_parser('show_audio')` and `@register_http('show_audio')`
  - Renders audio information for CLI and web

- **`add_audio.py`**: Create audio action (single file from path)
- **`add_audios.py`**: Batch create audio action (from folder)
- **`upload_audio.py`**: MCP upload handler (multipart uploads)
- **`modify_audio_caption.py`**: Update caption action (type-specific)
- **`delete_audio.py`**: Delete audio action
- **`set_audio_visibility.py`**: Update visibility action
- **`audio_quality_tiers.py`**: Quality tier definitions ✅ COMPLETE
  - Defines quality tiers: `standard` (192 kbps), `high` (320 kbps), `medium` (192 kbps), `low` (128 kbps)
  - All tiers use AAC format in M4A container
  - Used by `audio_transcode` maintenance job to generate all quality tiers
  - Standard format constants: `AUDIO_STANDARD_FORMAT`, `AUDIO_STANDARD_EXTENSION`, `AUDIO_STANDARD_MIME_TYPE`
- **`audio_utils.py`**: Audio processing utilities ✅ COMPLETE
  - `validate_audio_file()`: Validates audio files using `mutagen`
  - `get_audio_info()`: Extracts metadata (duration, bitrate, channels, sample_rate)
  - `transcode_to_aac()`: Transcodes audio to AAC format using ffmpeg
  - `create_date_directory()`: Creates date-based directory structure
  - Dependencies: `mutagen` (Python package), `ffmpeg` (system binary)
- **`mcp_utils.py`**: MCP tool registrations
  - `@register_mcp_tool` for all audio operations
  - Tier-based access control

### 3. Storage Directory ✅ COMPLETE

**Status**: Directory creation has been implemented in `hh/deploy/users/install.py`

**Installation System** (`hh/deploy/users/install.py`):

- `setup_audio_directory()` function creates `/srv/audio/{project_name}/` directory
- Creates `deleted/` subdirectory for soft deletes
- Permissions: `0o2775` (setgid for group write)
- Ownership: `{project_name}_root:{project_name}_admin`
- Called during installation process after files directory setup

### 4. Flask Routes ✅ COMPLETE

**Status**: Flask routes have been implemented in `hh/deploy/flask/app.py` (see "File System Refinement" section above for details)

### 5. Page Integration ✅ COMPLETE

**File**: `hh/page/page.py`

**Add methods:**
- ✅ `add_audio(file_path: str, caption: Optional[str] = None) -> Optional[int]`
  - Creates audio record in database
  - Adds audio to page's audio group
  - Calls `audio.process_upload()` to handle file processing
  - Mirrors `page.add_image()` pattern exactly
  - Returns audio_id on success

- ✅ `get_audio_data(rebuild: bool = False) -> List[Dict[str, Any]]`
  - Queries `audio_groups` table
  - Returns list of audio items with rank, metadata
  - Cached in `self.audio` field
  - Similar to `get_images_data()` and `get_files_data()`

- ✅ Generalized media operations: `copy_media_items()`, `move_media_items()`, `remove_media_item()`, `set_media_rank()`
  - Support all media types (image, file, audio, video) via `media_type` parameter
  - Use dynamic helper methods to resolve table names, field names, and methods based on media type
  - Replaced old specific methods (`copy_images`, `copy_files`, `move_images`, `move_files`, `remove_image`, `remove_file`, `set_image_rank`, `set_file_rank`)
  - All action scripts call generalized methods directly with appropriate `media_type` argument

- ✅ Helper methods: `_get_audio_by_class()`, `_remove_audio_from_group()`, `_flag_related_audio()`, `_create_audio_record()`, `_add_audio_to_group()`

**Update `show_page()` method:**
- ✅ Add `audio` field to response data
- ✅ Call `get_audio_data()` and include in response

**File**: `hh/page/render_show_page.py`

**Add `render_audio_section()` function:**
- Renders audio group table
- Similar to `render_images_section()` and `render_files_section()`
- Adds audio links that open audio viewer overlay
- Supports view toggle (table/tile views)

### 6. TypeScript Components

**File**: `hh/deploy/site/ts/audio-viewer.ts`

- Overlay component for audio playback
- Uses `mode: 'pannable'` or appropriate mode
- HTML5 `<audio>` element for playback
- Displays metadata (duration, bitrate, etc.)
- Caption display
- Links to `/audio/<id>` page

**File**: `hh/deploy/site/ts/audio-group-sorter.ts`

- Specialized browser for sorting audio within page's audio group
- Drag-and-drop reordering using SortableJS
- Similar to `image-group-sorter.ts`
- Incremental rank updates via MCP

**File**: `hh/deploy/site/ts/page-actions-audio.ts`

- Action handlers for audio operations
- `copy_audio_app()`, `move_audio_app()`, `sort_audio_app()`
- Browser integration for selection
- Similar to `page-actions-images.ts`

### 7. Upload Handler

**File**: `hh/deploy/site/ts/upload-handler-audio.ts`

- Specialized upload handler for audio files
- MIME type validation (audio/*)
- Multiple file selection
- Upload progress tracking
- Sequential processing via MCP
- Creates preview clips as background task (optional)

### 8. MCP Tools

**File**: `hh/audio/mcp_utils.py`

Register tools with appropriate tiers:
- `show_audio` - View audio (tiers 1-4, 7-8)
- `add_audio` - Upload audio (tiers 3-4, 7-8)
- `modify_audio_caption` - Update caption (tiers 3-4, 7-8)
- `delete_audio` - Delete audio (tiers 3-4, 7-8)
- `modify_audio_visibility` - Update visibility (tiers 3-4, 7-8)
- `set_audio_rank` - Update rank in group (tiers 3-4, 7-8)
- `copy_audio_app`, `move_audio_app`, `sort_audio_app` - App actions (tiers 7-8)

### 9. Cache System

**File**: `hh/audio/audio.py`

- Two-tier cache: hot cache (in-memory) + cache database
- Derived fields cached: `instances`, `pages` (usage), `metadata` (backup)
- Lazy computation pattern
- Automatic cache refresh during gateway commit
- `_flag_cache_refresh()` method
- `_refresh_cached_audio()` method

## Video System Implementation

### 1. Database Schema ✅ COMPLETE

**Status**: Database schema has been implemented in `hh/deploy/db/init.sql` and `hh/deploy/db/init_cache.sql`

**Main Database Tables** (`hh/deploy/db/init.sql`):

```sql
CREATE TABLE IF NOT EXISTS `video` (
  `id` int NOT NULL AUTO_INCREMENT,
  `caption` varchar(255) DEFAULT NULL,
  `username` varchar(255) NOT NULL,
  `uploaded` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `viewCount` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `username` (`username`),
  KEY `uploaded` (`uploaded`),
  KEY `visibility` (`visibility`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `video_groups` (
  `page_id` int NOT NULL,
  `video_id` int NOT NULL,
  `video_rank` int NOT NULL,
  PRIMARY KEY (`page_id`, `video_id`, `video_rank`),
  KEY `idx_page_rank` (`page_id`, `video_rank`),
  KEY `idx_video` (`video_id`),
  CONSTRAINT `fk_video_groups_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_video_groups_video` FOREIGN KEY (`video_id`) REFERENCES `video` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `video_instances` (
  `video_id` int NOT NULL,
  `instance_type` varchar(32) NOT NULL,  -- 'full', 'thumbnail' (image file)
  `file_path` varchar(1024) NOT NULL,
  `mime_type` varchar(128) NOT NULL,
  `size_bytes` bigint NOT NULL,
  `width` int DEFAULT NULL,
  `height` int DEFAULT NULL,
  `duration_seconds` decimal(10,2) DEFAULT NULL,
  `bitrate` int DEFAULT NULL,
  KEY `idx_video_id` (`video_id`),
  CONSTRAINT `fk_video_instances_video` FOREIGN KEY (`video_id`) REFERENCES `video` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Cache Database Tables** (`hh/deploy/db/init_cache.sql`):

```sql
CREATE TABLE IF NOT EXISTS `video` (
  `id` int NOT NULL,
  `instances` json DEFAULT NULL,
  `pages` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Actual Implementation Notes:**
- Tables match the `images` and `files` pattern exactly
- Main database uses relational structure (no JSON metadata in main tables)
- Cache database uses JSON for derived fields (`instances`, `pages`, `metadata`)
- Foreign key constraints with CASCADE deletes
- Indexes on `username`, `uploaded`, `visibility` for common queries
- `video_instances` table includes: `video_id`, `instance_type`, `file_path`, `mime_type`, `size_bytes`, `width`, `height`, `duration_seconds`, `bitrate`
- `video_groups` table uses composite primary key: `(page_id, video_id, video_rank)`

### 2. Module Structure

Create `hh/video/` directory with same structure as `hh/audio/`:

- **`video.py`**: Video class
  - Methods: `__init__()`, `show_video()`, `get_video_data()`, `get_instances()`, `get_instances_data()`, `get_usage_data()`, `_refresh_cached_video()`, CRUD operations
  - Cache hydration from cache database
  - Lazy computation of derived fields
  - Instance management (full video, thumbnail)
  - `process_upload()` method: mimics image processing but simplified
    - MIME type validation (`video/*`)
    - File validation using `ffprobe` (if available)
    - Creates date-based directory structure
    - Saves full-size version (original file)
    - Extracts metadata (width, height, duration, bitrate) using `ffprobe`
    - Creates single instance entry in `video_instances` table (type='full')
    - Enqueues maintenance job (`video_transcode`) for background transcoding
    - Infrastructure ready for quality tier processing

- **`video_registry.py`**: Hot cache system
  - `get_video(video_id)` function
  - `refresh_stale_video_caches()` function
  - Module-level `_video_cache: Dict[int, Video]`

- **`show_video.py`**: Action handler
  - `@register_action('show_video')` and `@register_command('show_video')`
  - Loads video, calls `video.show_video()`, sets action response

- **`render_show_video.py`**: Backend handlers
  - `@register_parser('show_video')` and `@register_http('show_video')`
  - Renders video information for CLI and web

- **`add_video.py`**: Create video action (single file from path)
- **`add_videos.py`**: Batch create video action (from folder)
- **`upload_video.py`**: MCP upload handler (multipart uploads)
- **`modify_video_caption.py`**: Update caption action (type-specific)
- **`delete_video.py`**: Delete video action
- **`set_video_visibility.py`**: Update visibility action
- **`video_quality_tiers.py`**: Quality tier definitions ✅ COMPLETE
  - Defines quality tiers: `standard` (original dimensions, 2500 kbps), `high` (1920x1080, 5000 kbps), `medium` (1280x720, 2500 kbps), `low` (854x480, 1000 kbps)
  - All tiers use H.264 codec in MP4 container
  - Used by `video_transcode` maintenance job to generate all quality tiers
  - Standard format constants: `VIDEO_STANDARD_FORMAT`, `VIDEO_STANDARD_EXTENSION`, `VIDEO_STANDARD_MIME_TYPE`
- **`video_utils.py`**: Video processing utilities ✅ COMPLETE
  - `validate_video_file()`: Validates video files using `ffprobe`
  - `get_video_info()`: Extracts metadata (width, height, duration, bitrate)
  - `transcode_to_mp4()`: Transcodes video to MP4 (H.264) format using ffmpeg
  - `create_date_directory()`: Creates date-based directory structure
  - Dependencies: `ffmpeg` and `ffprobe` (system binaries)
- **`mcp_utils.py`**: MCP tool registrations
  - `@register_mcp_tool` for all video operations
  - Tier-based access control

### 3. Storage Directory ✅ COMPLETE

**Status**: Directory creation has been implemented in `hh/deploy/users/install.py`

**Installation System** (`hh/deploy/users/install.py`):

- `setup_video_directory()` function creates `/srv/video/{project_name}/` directory
- Creates `deleted/` subdirectory for soft deletes
- Permissions: `0o2775` (setgid for group write)
- Ownership: `{project_name}_root:{project_name}_admin`
- Called during installation process after audio directory setup

### 4. Flask Routes ✅ COMPLETE

**Status**: Flask routes have been implemented in `hh/deploy/flask/app.py` (see "File System Refinement" section above for details)

### 5. Page Integration ✅ COMPLETE

**File**: `hh/page/page.py`

**Add methods:**
- ✅ `add_video(file_path: str, caption: Optional[str] = None) -> Optional[int]`
  - Creates video record in database
  - Adds video to page's video group
  - Calls `video.process_upload()` to handle file processing
  - Mirrors `page.add_image()` pattern exactly
  - Returns video_id on success

- ✅ `get_video_data(rebuild: bool = False) -> List[Dict[str, Any]]`
  - Queries `video_groups` table
  - Returns list of video items with rank, metadata
  - Cached in `self.video` field
  - Similar to `get_images_data()` and `get_files_data()`

- ✅ Generalized media operations: `copy_media_items()`, `move_media_items()`, `remove_media_item()`, `set_media_rank()`
  - Support all media types (image, file, audio, video) via `media_type` parameter
  - Use dynamic helper methods to resolve table names, field names, and methods based on media type
  - Replaced old specific methods (`copy_images`, `copy_files`, `move_images`, `move_files`, `remove_image`, `remove_file`, `set_image_rank`, `set_file_rank`)
  - All action scripts call generalized methods directly with appropriate `media_type` argument

- ✅ Helper methods: `_get_video_by_class()`, `_remove_video_from_group()`, `_flag_related_video()`, `_create_video_record()`, `_add_video_to_group()`

**Update `show_page()` method:**
- ✅ Add `video` field to response data
- ✅ Call `get_video_data()` and include in response

**File**: `hh/page/render_show_page.py`

**Add `render_video_section()` function:**
- Renders video group table
- Similar to other media sections
- Adds video links that open video viewer overlay
- Supports view toggle (table/tile views)

### 6. TypeScript Components

**File**: `hh/deploy/site/ts/video-viewer.ts`

- Overlay component for video playback
- Uses `mode: 'pannable'` or appropriate mode
- HTML5 `<video>` element for playback
- Displays metadata (duration, resolution, bitrate, etc.)
- Caption display
- Links to `/video/<id>` page

**File**: `hh/deploy/site/ts/video-group-sorter.ts`

- Specialized browser for sorting video within page's video group
- Drag-and-drop reordering using SortableJS
- Similar to `image-group-sorter.ts` and `audio-group-sorter.ts`

**File**: `hh/deploy/site/ts/page-actions-video.ts`

- Action handlers for video operations
- `copy_video_app()`, `move_video_app()`, `sort_video_app()`
- Browser integration for selection

### 7. Upload Handler

**File**: `hh/deploy/site/ts/upload-handler-video.ts`

- Specialized upload handler for video files
- MIME type validation (video/*)
- Multiple file selection
- Upload progress tracking
- Sequential processing via MCP
- Creates thumbnails as background task (optional)

### 8. MCP Tools

**File**: `hh/video/mcp_utils.py`

Register tools with appropriate tiers:
- `show_video` - View video (tiers 1-4, 7-8)
- `add_video` - Upload video (tiers 3-4, 7-8)
- `modify_video_caption` - Update caption (tiers 3-4, 7-8)
- `delete_video` - Delete video (tiers 3-4, 7-8)
- `modify_video_visibility` - Update visibility (tiers 3-4, 7-8)
- `set_video_rank` - Update rank in group (tiers 3-4, 7-8)
- `copy_video_app`, `move_video_app`, `sort_video_app` - App actions (tiers 7-8)

### 9. Cache System

**File**: `hh/video/video.py`

- Two-tier cache: hot cache (in-memory) + cache database
- Derived fields cached: `instances`, `pages` (usage), `metadata` (backup)
- Lazy computation pattern
- Automatic cache refresh during gateway commit

## Implementation Details

### Streaming Routes

**HTTP Range Requests Support:**

Flask routes for `/audio/<id>/stream` and `/video/<id>/stream` should:
- Use `send_file()` with `conditional=True` (enables range request support)
- Set proper MIME types from metadata
- Support seeking via HTTP `Range` header
- Return `206 Partial Content` for range requests
- Return `200 OK` with full file for non-range requests

**Example pattern:**
```python
@app.route('/audio/<int:audio_id>/stream', methods=['GET'])
def stream_audio(audio_id: int):
    # Get metadata via download backend
    # Load audio file from disk
    # Return with send_file(conditional=True, mimetype=mime_type)
```

### Instance Processing ✅ COMPLETE

**Audio Instances:**
- `full`: Original audio file (created immediately on upload)
- `standard`: AAC format, 192 kbps (generated by background maintenance task)
- `high`: AAC format, 320 kbps (generated by background maintenance task)
- `medium`: AAC format, 192 kbps (generated by background maintenance task)
- `low`: AAC format, 128 kbps (generated by background maintenance task)

**Video Instances:**
- `full`: Original video file (created immediately on upload)
- `standard`: MP4 (H.264), original dimensions, 2500 kbps (generated by background maintenance task)
- `high`: MP4 (H.264), 1920x1080, 5000 kbps (generated by background maintenance task)
- `medium`: MP4 (H.264), 1280x720, 2500 kbps (generated by background maintenance task)
- `low`: MP4 (H.264), 854x480, 1000 kbps (generated by background maintenance task)

**Processing Workflow:**
1. Upload: Original file saved as 'full' instance (immediate, allows immediate streaming)
2. Background task: Transcode to all quality tiers (async, via maintenance job queue)
3. All instances stored in `audio_instances`/`video_instances` tables
4. Cached in cache database `instances` JSON field

**Maintenance Jobs:**
- `audio_transcode`: Processes `audio_transcode` jobs from maintenance job queue
  - Reads quality tiers from `AUDIO_QUALITY_TIERS` config
  - Creates all missing quality tiers in one job run
  - Transcodes from 'full' instance to AAC format
  - Creates instance entries for each successfully transcoded tier
- `video_transcode`: Processes `video_transcode` jobs from maintenance job queue
  - Reads quality tiers from `VIDEO_QUALITY_TIERS` config
  - Creates all missing quality tiers in one job run
  - Transcodes from 'full' instance to MP4 (H.264) format
  - Creates instance entries for each successfully transcoded tier

### Metadata Storage

**JSON Metadata Fields:**

Store in `metadata` JSON column (backed up in cache database):

**Audio:**
- `duration_seconds`: Audio length
- `bitrate`: Audio bitrate
- `codec`: Audio codec (e.g., "mp3", "aac", "opus")
- `sample_rate`: Sample rate in Hz
- `channels`: Number of audio channels

**Video:**
- `duration_seconds`: Video length
- `bitrate`: Video bitrate
- `codec`: Video codec (e.g., "h264", "vp9")
- `width`: Video width in pixels
- `height`: Video height in pixels
- `fps`: Frames per second
- `audio_codec`: Audio codec in video
- `audio_bitrate`: Audio bitrate in video

### MIME Type Validation

**Upload Handlers:**

- **Audio Uploader**: Validates `audio/*` MIME types
- **Video Uploader**: Validates `video/*` MIME types
- **Image Uploader**: Already exists, validates `image/*` MIME types
- **File Uploader**: Accepts any MIME type (generic files)

**Validation:** ✅ COMPLETE
- Check MIME type matches file extension (`audio/*` or `video/*`)
- Verify file is actually the claimed type:
  - Audio: Uses `mutagen` library to validate audio file structure
  - Video: Uses `ffprobe` to validate video file structure
- Extract metadata during validation:
  - Audio: duration, bitrate, channels, sample_rate (via `mutagen`)
  - Video: width, height, duration, bitrate (via `ffprobe`)
- Reject invalid files with clear error messages
- Process only after validation passes
- Dependencies: `mutagen` (Python package), `ffmpeg`/`ffprobe` (system binaries)

### Route Structure Summary

**Final Route Pattern:**

- `/img/<id>` - Show image page
- `/img/<id>/download` - Download full-size image
- `/file/<id>` - Show file page (changed from direct download)
- `/file/<id>/download` - Download file
- `/audio/<id>` - Show audio page
- `/audio/<id>/stream` - Stream audio for playback
- `/video/<id>` - Show video page
- `/video/<id>/stream` - Stream video for playback

## Implementation Order

1. **File System Refinement** ✅ COMPLETE
   - ✅ Update Flask routes (`/file/<id>`, `/file/<id>/download`, `/img/<id>/download`)
   - ✅ Add Flask routes for audio and video (`/audio/<id>`, `/audio/<id>/stream`, `/video/<id>`, `/video/<id>/stream`)
   - ✅ Disable NGINX direct file serving
   - ✅ Create `show_file` action and backend handlers (`hh/file/show_file.py`, `hh/file/render_show_file.py`)
   - Test file download flow

2. **Maintenance Daemon Updates** ✅ COMPLETE
   - ✅ Created `audio_cache_refresh.py` module
   - ✅ Created `video_cache_refresh.py` module
   - ✅ Created `audio_transcode.py` maintenance job handler
   - ✅ Created `video_transcode.py` maintenance job handler
   - ✅ Updated `maintenance_jobs_status.py` to include `stale_audio` and `stale_video` counts
   - ✅ Updated `worker.py` to include audio and video cache refresh in work docket
   - ✅ Updated `config_labels.py` with audio and video cache refresh labels, transcoding labels
   - ✅ Updated stale counts logging in worker.py
   - ✅ Worker automatically picks up `audio_transcode` and `video_transcode` job types

3. **Audio System**
   - ✅ Database schema (main + cache)
   - ✅ Flask routes
   - ✅ Maintenance daemon cache refresh
   - ✅ Audio class and registry (`hh/audio/audio.py`, `hh/audio/audio_registry.py`)
   - ✅ Entry points: `add_audio.py`, `add_audios.py`, `upload_audio.py` (all three like images)
   - ✅ Basic CRUD operations (`modify_audio_caption.py`, `delete_audio.py`, `set_audio_visibility.py`)
   - ✅ `show_audio` action and backend (`show_audio.py`, `render_show_audio.py`)
   - ✅ Quality tiers file (`audio_quality_tiers.py`) - for future use, currently unused
   - ✅ Page integration (`add_audio()` method + `get_audio_data()` to `hh/page/page.py`)
   - ✅ Config labels (`hh/audio/config_labels.py`)
   - ✅ MCP tools (`hh/audio/mcp_utils.py`)
   - ✅ Cache system (integrated into audio class)
   - ✅ Processing: `process_upload()` creates date-based directories, saves full file, creates single 'full' instance entry, enqueues transcoding job
   - ✅ File validation: Uses `mutagen` library for audio file validation and metadata extraction
   - ✅ Processing utilities: `audio_utils.py` with validation, metadata extraction, and transcoding functions
   - ✅ Quality tiers: `audio_quality_tiers.py` defines all quality tiers (standard, high, medium, low)
   - ✅ Maintenance job handler: `audio_transcode.py` creates all quality tiers via background processing
   - ✅ Job enqueueing: `process_upload()` automatically enqueues `audio_transcode` job
   - ✅ Python backend actions: `copy_audio.py`, `copy_audios.py`, `move_audio.py`, `move_audios.py`, `remove_audio.py`, `set_audio_rank.py` - COMPLETE (singular and plural versions)
   - ✅ Page class methods: Generalized `copy_media_items()`, `move_media_items()`, `remove_media_item()`, `set_media_rank()` support audio via `media_type` parameter - COMPLETE
   - ✅ MCP tool registrations: All audio operations registered in `hh/page/mcp_utils.py` - COMPLETE
   - ✅ Parser registrations: All audio operations registered in `hh/page/render_show_page.py` - COMPLETE
   - ✅ TypeScript components (viewer) - COMPLETE (`audio-viewer.ts`)
   - ✅ TypeScript components (sorter, actions) - COMPLETE
   - ✅ Upload handler TypeScript - COMPLETE (extended existing handler)

4. **Video System**
   - ✅ Database schema (main + cache)
   - ✅ Flask routes
   - ✅ Maintenance daemon cache refresh
   - Video class and registry (`hh/video/video.py`, `hh/video/video_registry.py`)
   - Entry points: `add_video.py`, `add_videos.py`, `upload_video.py` (all three like images)
   - Basic CRUD operations (`modify_video_caption.py`, `delete_video.py`, `set_video_visibility.py`)
   - `show_video` action and backend (`show_video.py`, `render_show_video.py`)
   - Quality tiers file (`video_quality_tiers.py`) - for future use, currently unused
   - Page integration (`add_video()` method + `get_video_data()` to `hh/page/page.py`)
   - ✅ Python backend actions: `copy_video.py`, `copy_videos.py`, `move_video.py`, `move_videos.py`, `remove_video.py`, `set_video_rank.py` - COMPLETE (singular and plural versions)
   - ✅ Page class methods: Generalized `copy_media_items()`, `move_media_items()`, `remove_media_item()`, `set_media_rank()` support video via `media_type` parameter - COMPLETE
   - ✅ MCP tool registrations: All video operations registered in `hh/page/mcp_utils.py` - COMPLETE
   - ✅ Parser registrations: All video operations registered in `hh/page/render_show_page.py` - COMPLETE
   - ✅ TypeScript components (viewer) - COMPLETE (`video-viewer.ts`)
   - ✅ TypeScript components (sorter, actions) - COMPLETE
   - ✅ Upload handler TypeScript - COMPLETE (extended existing handler)
   - ✅ Cache system (integrated into video class)
   - ✅ Processing: `process_upload()` creates date-based directories, saves full file, creates single 'full' instance entry, enqueues transcoding job
   - ✅ File validation: Uses `ffprobe` for video file validation and metadata extraction
   - ✅ Processing utilities: `video_utils.py` with validation, metadata extraction, and transcoding functions
   - ✅ Quality tiers: `video_quality_tiers.py` defines all quality tiers (standard, high, medium, low)
   - ✅ Maintenance job handler: `video_transcode.py` creates all quality tiers via background processing
   - ✅ Job enqueueing: `process_upload()` automatically enqueues `video_transcode` job

4. **Code Generalization** ✅ COMPLETE
   - ✅ Generalized media operations in `Page` class: `copy_media_items()`, `move_media_items()`, `remove_media_item()`, `set_media_rank()`
   - ✅ Removed redundant specific methods (`copy_images`, `copy_files`, `move_images`, `move_files`, `remove_image`, `remove_file`, `set_image_rank`, `set_file_rank`)
   - ✅ All action scripts updated to call generalized methods with `media_type` parameter
   - ✅ Created missing file operations: `copy_file.py`, `move_file.py`, `add_file.py`, `add_files.py` to match image/audio/video pattern
   - ✅ Updated MCP tool registrations for all media types (singular and plural versions)
   - ✅ Updated parser registrations in `render_show_page.py`
   - ✅ All media types now have consistent API: singular and plural copy/move/add operations, remove, and set_rank

5. **Future Work** (Not in scope)
   - Unified media viewer overlay (handles all types)
   - TypeScript components for audio/video (viewer, sorter, actions, upload handlers)
   - Playlist functionality
   - Optional: Soft-delete original files after successful transcoding
   - Optional: Preview clips for audio (10-second clips)
   - Optional: Thumbnail extraction for video

## Design Decisions

1. **Instances Tables**: YES for both audio and video ✅ COMPLETE
   - Audio: Full (original) + standard/high/medium/low quality tiers (AAC format)
   - Video: Full (original) + standard/high/medium/low quality tiers (MP4 H.264 format)
   - Full instance created immediately on upload (enables immediate streaming)
   - Quality tiers generated as background maintenance tasks via job queue
   - All tiers stored in `audio_instances`/`video_instances` tables

2. **Separate Uploaders**: YES
   - Explicit audio uploader, video uploader, image uploader, file uploader
   - MIME type validation at upload time
   - Type-specific processing

3. **Streaming vs Download**: 
   - Audio/Video: Stream (playback in browser)
   - Files: Download (save to disk)
   - Images: Download (via `/img/<id>/download` route)

4. **Range Requests**: Supported for streaming routes
   - Enables seeking in audio/video players
   - Standard HTTP feature, Flask handles automatically with `conditional=True`

5. **Metadata**: Stored in JSON `metadata` field
   - Document-style storage
   - Flexible schema
   - Backed up in cache database

6. **NGINX Direct Serving**: Disabled for files
   - All file access goes through Flask routes
   - Enables gating, logging, access control
   - Images can remain direct-served for now (can be changed later)

## Notes

- All new systems follow existing image/file patterns exactly
- Code is highly copy-pasteable with minimal modifications
- TypeScript components follow existing overlay patterns
- MCP tools follow existing registration patterns
- Cache system follows existing two-tier pattern
- Page integration follows existing group pattern

This plan provides a complete roadmap for implementing multimedia support while maintaining consistency with the existing architecture.
