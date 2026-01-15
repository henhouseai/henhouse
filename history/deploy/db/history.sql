-- ============================================================
-- History Module Schema (Separate History Database)
-- Module: history
-- Database: history (separate database)
-- ============================================================

-- This schema creates the history database and its tables.
-- This is a skeleton/placeholder for testing the module DB system.

-- ============================================================
-- PAGE_HISTORY TABLE
-- Captures all page CRUD operations
-- ============================================================

CREATE TABLE page_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- What was modified
    page_id INT NOT NULL,
    operation ENUM('create', 'update', 'delete') NOT NULL,

    -- Who made the change
    user_tier INT NOT NULL,                  -- 1=guest, 2=verified, 3=admin, 4=root
    username VARCHAR(255) NULL,              -- henhouse_admin@host, etc.

    -- When
    recorded_ts DATETIME NOT NULL,

    -- What changed (JSON snapshot)
    before_state JSON NULL,                  -- NULL for create
    after_state JSON NULL,                   -- NULL for delete

    -- Indexing
    INDEX idx_page (page_id),
    INDEX idx_recorded (recorded_ts),
    INDEX idx_operation (operation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- MEDIA_HISTORY TABLE
-- Captures all media (image/file/audio/video) operations
-- ============================================================

CREATE TABLE media_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- What was modified
    media_type ENUM('image', 'file', 'audio', 'video') NOT NULL,
    media_id INT NOT NULL,
    operation ENUM('create', 'delete') NOT NULL,  -- Media doesn't update

    -- Who made the change
    user_tier INT NOT NULL,
    username VARCHAR(255) NULL,

    -- When
    recorded_ts DATETIME NOT NULL,

    -- What changed
    media_path VARCHAR(500) NULL,            -- File path for reference

    -- Indexing
    INDEX idx_media (media_type, media_id),
    INDEX idx_recorded (recorded_ts),
    INDEX idx_operation (operation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
