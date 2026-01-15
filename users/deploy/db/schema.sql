-- ============================================================
-- Henhouse Users Module Schema
-- Module: users
-- Database: main (adds tables to main database)
-- ============================================================

-- This schema adds user verification tables to the main database
-- for fast permission checking during CRUD operations.

-- ============================================================
-- CREDENTIALS TABLE
-- Stores verified user credentials (email, oauth, etc.)
-- These are login identifiers BEFORE a user gets a ~ page
-- ============================================================

CREATE TABLE credentials (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Credential type and value
    credential_type ENUM('email', 'oauth_google', 'oauth_github', 'oauth_other') NOT NULL,
    credential_value VARCHAR(255) NOT NULL,  -- email address or oauth identifier

    -- Verification status
    verified_ts DATETIME NULL,               -- NULL = not yet verified

    -- Link to ~ page (set when user becomes trusted)
    tilde_page_id INT NULL,                  -- FK to pages.id in main DB

    -- Timestamps
    created_ts DATETIME NOT NULL,
    last_active_ts DATETIME NOT NULL,

    -- Constraints
    UNIQUE KEY uniq_credential (credential_type, credential_value),
    INDEX idx_tilde (tilde_page_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SUBGROUPS TABLE
-- The KEYSTONE table - links credentials to groups
-- This is the single source of truth for group membership
-- ============================================================

CREATE TABLE subgroups (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Which user/group page owns this subgroup
    owner_page_id INT NOT NULL,              -- FK to pages.id in main DB

    -- Subgroup name (e.g., 'friends', 'alice', 'moderators')
    group_name VARCHAR(64) NOT NULL,

    -- Which credential is a member
    credential_id INT NOT NULL,

    -- When added
    added_ts DATETIME NOT NULL,

    -- Constraints
    UNIQUE KEY uniq_membership (owner_page_id, group_name, credential_id),
    INDEX idx_owner_group (owner_page_id, group_name),
    INDEX idx_credential (credential_id),

    FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- OWNERSHIP TABLES
-- Map content IDs from main DB to subgroup memberships
-- One table per content type: pages, images, files, audio, video
-- ============================================================

CREATE TABLE page_owners (
    page_id INT NOT NULL,                    -- FK to pages.id in main DB
    subgroup_id INT NOT NULL,                -- FK to subgroups.id

    PRIMARY KEY (page_id, subgroup_id),
    INDEX idx_page (page_id),

    FOREIGN KEY (subgroup_id) REFERENCES subgroups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE image_owners (
    image_id INT NOT NULL,                   -- FK to images.id in main DB
    subgroup_id INT NOT NULL,

    PRIMARY KEY (image_id, subgroup_id),
    INDEX idx_image (image_id),

    FOREIGN KEY (subgroup_id) REFERENCES subgroups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE file_owners (
    file_id INT NOT NULL,                    -- FK to files.id in main DB
    subgroup_id INT NOT NULL,

    PRIMARY KEY (file_id, subgroup_id),
    INDEX idx_file (file_id),

    FOREIGN KEY (subgroup_id) REFERENCES subgroups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE audio_owners (
    audio_id INT NOT NULL,                   -- FK to audio.id in main DB
    subgroup_id INT NOT NULL,

    PRIMARY KEY (audio_id, subgroup_id),
    INDEX idx_audio (audio_id),

    FOREIGN KEY (subgroup_id) REFERENCES subgroups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE video_owners (
    video_id INT NOT NULL,                   -- FK to video.id in main DB
    subgroup_id INT NOT NULL,

    PRIMARY KEY (video_id, subgroup_id),
    INDEX idx_video (video_id),

    FOREIGN KEY (subgroup_id) REFERENCES subgroups(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- MAGIC LINKS TABLE
-- For email verification via magic link authentication
-- ============================================================

CREATE TABLE magic_links (
    token VARCHAR(64) PRIMARY KEY,           -- Random secure token

    credential_id INT NOT NULL,              -- Which credential this verifies

    -- Timing
    created_ts DATETIME NOT NULL,
    expires_ts DATETIME NOT NULL,            -- Typically 15 minutes after created
    used_ts DATETIME NULL,                   -- Set when token is consumed

    -- Security
    ip_address VARCHAR(45) NOT NULL,         -- IPv4 or IPv6

    FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE CASCADE,
    INDEX idx_expires (expires_ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SESSIONS TABLE
-- Active user sessions
-- ============================================================

CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,      -- Random secure session ID

    credential_id INT NOT NULL,              -- Which credential owns this session

    -- Timing
    created_ts DATETIME NOT NULL,
    last_active_ts DATETIME NOT NULL,
    expires_ts DATETIME NOT NULL,            -- Session timeout

    -- Security
    ip_address VARCHAR(45) NOT NULL,

    FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE CASCADE,
    INDEX idx_credential (credential_id),
    INDEX idx_expires (expires_ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- CONTACT SUBMISSIONS TABLE
-- For contact form submissions (before user has ~ page)
-- ============================================================

CREATE TABLE contact_submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,

    credential_id INT NOT NULL,              -- Who submitted

    -- Submission content
    subject VARCHAR(255) NULL,
    message TEXT NOT NULL,

    -- Status
    status ENUM('pending', 'read', 'replied', 'archived', 'spam') DEFAULT 'pending',

    -- Timestamps
    submitted_ts DATETIME NOT NULL,
    read_ts DATETIME NULL,
    replied_ts DATETIME NULL,

    -- Admin who handled it
    handled_by_page_id INT NULL,             -- FK to admin's page.id
    reply_text TEXT NULL,

    FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_submitted (submitted_ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
