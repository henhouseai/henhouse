-- Migration: Replace image_summary and file_summary with unified media_summary column
-- Date: 2026-01-20
-- Purpose: Consolidate all media type caching into a single JSON column for dynamic expansion

-- Step 1: Add new media_summary column
ALTER TABLE pages ADD COLUMN media_summary json DEFAULT NULL AFTER children_summary;

-- Step 2: Drop old columns (data loss acceptable - cache will rebuild)
ALTER TABLE pages DROP COLUMN image_summary;
ALTER TABLE pages DROP COLUMN file_summary;

-- Step 3: Clear pages table to force cache rebuild with new format
TRUNCATE TABLE pages;

-- Note: After running this migration, the maintenance daemon will rebuild all caches
-- in the new format with media_summary containing dynamic top-level keys for each
-- registered media type (image, file, audio, video, etc.)
