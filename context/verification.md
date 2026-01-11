# Tier 2 Verification System

This document describes the architecture for Henhouse's verified user system - a comprehensive framework for allowing external users to contribute to a Henhouse deployment in controlled ways.

---

## Table of Contents

1. [Overview](#overview)
2. [Core Principles](#core-principles)
3. [Users as Pages](#users-as-pages)
4. [Groups Architecture](#groups-architecture)
5. [Database Architecture](#database-architecture)
6. [Schema Reference](#schema-reference)
7. [Permission Model](#permission-model)
8. [Media Ownership](#media-ownership)
9. [The Self-Group Pattern](#the-self-group-pattern)
10. [Multiple Credentials](#multiple-credentials)
11. [SubPage Class](#subpage-class)
12. [Module Structure](#module-structure)
13. [Authentication Flow](#authentication-flow)
14. [MCP Tools](#mcp-tools)
15. [Implementation Phases](#implementation-phases)
16. [Examples and Use Cases](#examples-and-use-cases)
17. [Integration with Existing Systems](#integration-with-existing-systems)
18. [Future Considerations](#future-considerations)

---

## Overview

The Henhouse verification system extends the existing 4-tier architecture (guest, verified, admin, root) by adding a rich application layer for tier 2 (verified) users. This enables external contributors to participate in a Henhouse deployment without admin/root access.

### What This System Enables

- **Contact forms**: Anonymous visitors can verify their email and submit messages
- **Comments**: Verified users can add comments to pages they have access to
- **User pages (~)**: Trusted users get their own space in the page hierarchy
- **Subgroups**: ~ users can create groups like `alice/friends` for fine-grained access
- **Collaborative editing**: Multiple users can share edit access to pages
- **Moderation**: Ownership cascades top-down; parent owners can always override children

### What This System Does NOT Do

- Does not modify the main database schema
- Does not replace admin/root tier functionality
- Does not implement algorithmic trust scoring
- Does not automatically grant ~ pages (always manual admin decision)

---

## Core Principles

### 1. Users ARE Pages

There is no separate "users" table in the main database. Users and groups are page class extensions, just like any other page type. They share the global link namespace.

```
example.com/alice       -> UserPage (class='user', link='alice')
example.com/moderators  -> GroupPage (class='group', link='moderators')
example.com/rubikscube  -> Regular page (class='page', link='rubikscube')
```

If `rubikscube` already exists as a content page, no user can claim that name.

### 2. Separate Database for Verification Logic

All verification-related data lives in a separate `{project}_user` database. The main database remains unchanged. This separation means:

- Verification is optional - don't create the user DB, no verification features
- Clean upgrade path - main schema never touched
- Can run on same host initially, scale to separate host later
- Follows the same pattern as cache DB

### 3. Lazy Permission Checking

Permissions are only checked when a tier-2 user attempts a CRUD operation. The system does not pre-build permission maps or cache user access. Every check is fresh:

1. Look up ownership for the content being modified
2. Check if requester's credential is in any owning subgroup
3. For pages: if no match, walk up parent chain and repeat
4. For media: no parent walk, direct check only
5. Return YES on first match, NO if exhausted without match

### 4. Top-Down Ownership

Ownership always flows from the root down. A parent owner can:

- Add/remove children from any page they own
- Change ownership of any child page
- Delete any child content
- Override any settings made by child owners

The root node (page id=1) owner has ultimate authority over everything.

### 5. Trust is Manual, Not Algorithmic

There is no `trust_level` field or automatic promotion. Trust is determined by:

- Does the credential exist and is it verified? → Can use basic tier-2 features
- Is the credential in groups that own content? → Can edit that content
- Does the credential have a `tilde_page_id` set? → Has a ~ page, can create subgroups

Admin/root tier humans manually:
- Grant ~ pages to trusted users
- Add users to system-wide groups (moderators, etc.)
- Revoke access when needed

---

## Users as Pages

### Inheritance Pattern

This follows the legacy PPW system's Person/Company pattern, where Company extends Person:

```python
@register_page_class('user')
class UserPage(Page):
    """
    A verified user with a ~ page.

    User-specific data is stored in the page's metadata JSON field,
    following Henhouse's document-DB pattern. Examples:
    - display_name
    - bio
    - website
    - social_links
    - preferences
    """

    @classmethod
    def allow_null_names(cls) -> bool:
        return False  # Users must have names (their username)

    @classmethod
    def auto_link_name(cls) -> bool:
        return True  # Link matches name (alice -> /alice)

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        return False  # Usernames must be unique

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        return parent_class == 'users_container'  # Only under designated parent


@register_page_class('company')
class CompanyPage(UserPage):
    """
    A business/organization account - extends user.

    Like Instagram's "upgrade to business account" feature.
    Gets all UserPage behavior, can add company-specific fields:
    - company_name
    - tax_id
    - business_type
    - employees (links to other users)
    """
    pass  # Inherits from UserPage, can override methods as needed


@register_page_class('group')
class GroupPage(Page):
    """
    A top-level group (admins, moderators, etc.).

    Groups are pages too - they share the link namespace.
    Group membership is tracked in the user database's subgroups table.
    """

    @classmethod
    def allow_null_names(cls) -> bool:
        return False

    @classmethod
    def auto_link_name(cls) -> bool:
        return True

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        return False  # Group names must be unique

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        return parent_class == 'groups_container'
```

### Metadata Storage

User-specific fields are stored in the page's `text` field as JSON metadata, following Henhouse's document-DB pattern. The page class extracts these in `_after_metadata_extraction()`:

```python
def _after_metadata_extraction(self):
    super()._after_metadata_extraction()
    # Extract user-specific fields from metadata
    self.display_name = self.get_metadata_value('display_name')
    self.bio = self.get_metadata_value('bio')
    self.website = self.get_metadata_value('website')
    # etc.
```

### URL Mapping

Since users are pages with auto-linked names:

```
example.com/alice           -> User page for alice
example.com/alice?edit=1    -> Edit mode (if authorized)
example.com/alice?log=1     -> With debug logs
```

The existing page routing handles this naturally.

---

## Groups Architecture

### Two Levels of Groups

**Level 1: Top-Level Groups (Pages)**

These are GroupPage instances that share the global link namespace:

```
/admins      -> GroupPage, link='admins'
/moderators  -> GroupPage, link='moderators'
/editors     -> GroupPage, link='editors'
```

Top-level groups are created by admin/root users. They work just like user pages but represent a collection of users rather than a single user.

**Level 2: User Subgroups (Relational)**

These are NOT pages. They exist only in the user database's `subgroups` table:

```
alice/friends         -> Rows in subgroups where owner_page_id=alice's page id
alice/trusted-collabs -> Same pattern
moderators/content    -> Subgroup under the moderators group page
```

User subgroups cannot be navigated to via URL. They're internal organizational structures.

### Group Membership

All group membership (both top-level and subgroups) is tracked in the `subgroups` table:

```sql
-- Alice is in the moderators group
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (moderators_page_id, 'moderators', alice_credential_id, NOW());

-- Bob is in alice's friends subgroup
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (alice_page_id, 'friends', bob_credential_id, NOW());
```

The convention for top-level group membership is that the `group_name` matches the group's link. So "moderators" group has members in subgroups where `group_name='moderators'` and `owner_page_id` is the moderators page id.

---

## Database Architecture

### Cluster Topology

The user database fits into the existing cluster architecture:

```
Current Deployment (Single Box):
┌─────────────────────────────────────────┐
│                nginx box                │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ main_db │ │cache_db │ │  user_db  │  │
│  └─────────┘ └─────────┘ └───────────┘  │
└─────────────────────────────────────────┘

Future Scaled Deployment:
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ nginx   │   │ main_db │   │cache_db │   │ user_db │
│  box    │   │   box   │   │   box   │   │   box   │
└─────────┘   └─────────┘   └─────────┘   └─────────┘
      │             │             │             │
      └─────────────┴─────────────┴─────────────┘
                    shared network

Future Additions:
┌───────────┐   ┌──────────────┐
│history_db │   │backup_worker │
│    box    │   │     box      │
└───────────┘   └──────────────┘
```

### Connection Routing

The user database connection follows the same pattern as cache_db:

```python
# In connection.py, add user_db DSN loading
def _get_user_dsn(project_name: str) -> Optional[Dict]:
    """Get user database DSN from config."""
    # Similar to _get_cache_dsn() pattern
    # Reads from user config: user_host, mysql_user_password, etc.
```

### Configuration

Add to `install.cnf`:

```ini
# User/Session Database
user_host = localhost                    # Same as db_host initially
mysql_user_password = CHANGE_ME          # Separate password
user_ssl_ca_path = /path/to/ca.pem       # If TLS enabled

# Verification Features (optional)
enable_verified_users = 1                # Master switch
enable_contact_forms = 1                 # Contact form submissions
enable_user_comments = 1                 # Comments on pages
enable_tilde_pages = 1                   # ~ pages for trusted users
```

---

## Schema Reference

### User Database Complete Schema

```sql
-- ============================================================
-- Henhouse User Database Schema
-- Database: {project}_user
-- ============================================================

CREATE DATABASE IF NOT EXISTS {project}_user;
USE {project}_user;

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
```

---

## Permission Model

### The YES/NO Question

All permission checks boil down to one question:

> "Does this credential have membership in any subgroup that owns this content?"

The answer is YES or NO. There are no partial permissions, no read-only vs read-write distinctions at this level. If you're in an owning group, you can CRUD. If not, you can't.

### Page Permission Check

For pages, the check includes walking up the parent chain:

```python
def can_edit_page(credential_id: int, page_id: int) -> bool:
    """
    Check if credential can edit this page.

    Algorithm:
    1. Look for direct ownership match
    2. If not found, check parent page
    3. Repeat until root or match found
    4. Return YES on first match, NO if exhausted
    """

    # Check direct ownership
    result = user_db.fetchone("""
        SELECT 1 FROM page_owners po
        JOIN subgroups sg ON po.subgroup_id = sg.id
        WHERE po.page_id = %s AND sg.credential_id = %s
        LIMIT 1
    """, (page_id, credential_id))

    if result:
        return True  # YES - direct ownership match

    # Get parent and recurse
    parent_row = main_db.fetchone(
        "SELECT parent FROM pages WHERE id = %s", (page_id,)
    )

    if parent_row and parent_row[0]:
        return can_edit_page(credential_id, parent_row[0])

    return False  # NO - reached root without match


def can_delete_page(credential_id: int, page_id: int) -> bool:
    """Same as edit - if you can edit, you can delete."""
    return can_edit_page(credential_id, page_id)


def can_add_child(credential_id: int, parent_page_id: int) -> bool:
    """
    Check if credential can add a child under this page.
    Same as checking if they can edit the parent.
    """
    return can_edit_page(credential_id, parent_page_id)
```

### Media Permission Check

For images, files, audio, and video, there is **no parent chain walking**. Each asset has explicit ownership:

```python
def can_delete_image(credential_id: int, image_id: int) -> bool:
    """
    Check if credential can delete this image.
    Only the uploader (owner) can delete.
    NO parent chain walking - direct check only.
    """
    result = user_db.fetchone("""
        SELECT 1 FROM image_owners io
        JOIN subgroups sg ON io.subgroup_id = sg.id
        WHERE io.image_id = %s AND sg.credential_id = %s
        LIMIT 1
    """, (image_id, credential_id))

    return result is not None


def can_add_image_to_page(credential_id: int, page_id: int) -> bool:
    """
    Check if credential can add an image to this page.
    Anyone who can edit the page can add images to it.
    """
    return can_edit_page(credential_id, page_id)
```

### Ownership Usurpation

Parent owners can always override child owners:

```python
def usurp_ownership(admin_credential_id: int, page_id: int, new_owner_subgroup_id: int) -> bool:
    """
    Change ownership of a page.

    Caller must have edit access (via parent chain).
    This removes existing ownership and sets new owner.
    """
    if not can_edit_page(admin_credential_id, page_id):
        return False

    # Clear existing ownership
    user_db.execute("DELETE FROM page_owners WHERE page_id = %s", (page_id,))

    # Set new ownership
    user_db.execute(
        "INSERT INTO page_owners (page_id, subgroup_id) VALUES (%s, %s)",
        (page_id, new_owner_subgroup_id)
    )

    return True
```

---

## Media Ownership

### Key Differences from Pages

1. **No parent chain**: Images, files, audio, video are not hierarchical. Ownership is direct.
2. **Uploader owns**: When a verified user uploads media, they become the owner.
3. **Can share but not transfer**: Owner can add others to view/use, but ownership doesn't cascade.
4. **Page edit != media delete**: Having edit access to a page doesn't let you delete images attached to it (unless you own them).

### Example Flow

```
1. Alice uploads photo.jpg to /community/events
   - photo.jpg gets image_id = 500
   - INSERT INTO image_owners (image_id, subgroup_id)
     VALUES (500, alice_self_subgroup_id)
   - Photo is now attached to page /community/events

2. Bob wants to delete Alice's photo
   - Bob has edit access to /community/events
   - Bob can remove the image from the page (edit image_groups)
   - Bob CANNOT delete the image file itself (not owner)

3. Alice wants to delete her photo
   - Alice checks can_delete_image(alice_cred, 500) -> YES
   - Image is deleted from images table and all image_groups
```

### Group Images/Files Table Editing

When a verified user has edit access to a page, they can:
- Add images/files to that page (via image_groups, file_groups, etc.)
- Remove images/files from that page
- Reorder images/files on that page

They cannot:
- Delete the actual image/file record (only owner can)
- Modify the image/file itself (caption, etc.) unless they're owner

---

## The Self-Group Pattern

### Concept

Every user with a ~ page has a "self-group" - a subgroup named after themselves that contains their own credentials. This is how the system knows "alice" the owner equals the person logging in with alice@email.com.

### Setup Flow

When admin grants alice a ~ page:

```sql
-- 1. Alice already has a verified credential
SELECT id FROM credentials WHERE credential_value = 'alice@email.com';
-- Returns credential_id = 5

-- 2. Admin creates user page
-- Via MCP: add_page parent=/users class=user name="alice"
-- Returns page_id = 100

-- 3. Link credential to ~ page
UPDATE credentials SET tilde_page_id = 100 WHERE id = 5;

-- 4. Create alice's self-group
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (100, 'alice', 5, NOW());
-- Returns subgroup_id = 1

-- 5. Give alice ownership of her own page
INSERT INTO page_owners (page_id, subgroup_id) VALUES (100, 1);
```

Now when alice logs in with alice@email.com:
- Session lookup finds credential_id = 5
- Checking can_edit_page(5, 100):
  - page_owners has (100, 1)
  - subgroups row 1 has credential_id = 5
  - Match! Alice can edit her page.

### Why "Self-Group"?

The self-group pattern means:
- Ownership references are always to subgroups, never directly to credentials
- A user can add multiple credentials to their self-group (email + oauth)
- The same permission logic works for everything

---

## Multiple Credentials

### Linking Multiple Auth Methods

A user can have multiple ways to authenticate, all linked to the same identity:

```sql
-- Alice has email
INSERT INTO credentials (credential_type, credential_value, verified_ts, tilde_page_id, created_ts, last_active_ts)
VALUES ('email', 'alice@email.com', NOW(), 100, NOW(), NOW());
-- credential_id = 5

-- Alice adds Google OAuth
INSERT INTO credentials (credential_type, credential_value, verified_ts, tilde_page_id, created_ts, last_active_ts)
VALUES ('oauth_google', 'google-oauth-id-12345', NOW(), 100, NOW(), NOW());
-- credential_id = 6

-- Both credentials go in alice's self-group
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (100, 'alice', 5, NOW()), (100, 'alice', 6, NOW());
```

Now alice can log in via email magic link OR Google OAuth, and both sessions have the same access.

### Organization/Company Pattern

For a company account where multiple people need access:

```sql
-- Acme Corp has page_id = 200

-- Employee 1 (alice)
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (200, 'acme', 5, NOW());

-- Employee 2 (bob)
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (200, 'acme', 10, NOW());

-- Employee 3 (carol)
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (200, 'acme', 15, NOW());

-- Acme's page is owned by the acme self-group
INSERT INTO page_owners (page_id, subgroup_id) VALUES (200, acme_subgroup_id);
```

All three employees can edit Acme's page.

### Fine-Grained Organization Access

Within an organization, different access levels:

```sql
-- Acme has subgroups for different roles
-- acme/acme = full access (the self-group)
-- acme/editors = can edit content
-- acme/viewers = read-only (not implemented yet, but pattern is ready)

-- Alice is admin (in self-group)
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (200, 'acme', 5, NOW());

-- Bob is editor
INSERT INTO subgroups (owner_page_id, group_name, credential_id, added_ts)
VALUES (200, 'editors', 10, NOW());

-- Different pages have different ownership
-- Main company page owned by acme/acme
INSERT INTO page_owners (page_id, subgroup_id) VALUES (200, acme_self_subgroup_id);

-- Blog page owned by acme/editors
INSERT INTO page_owners (page_id, subgroup_id) VALUES (201, acme_editors_subgroup_id);
```

---

## SubPage Class

### The Problem

Currently, Henhouse URLs are single-segment plus query params:

```
example.com/alice?log=1
example.com/rubikscube?edit=1
```

We want tree-structured URLs without polluting the global link namespace:

```
example.com/alice/projects/proj1
example.com/docs/getting-started/installation
```

### The Solution

A `subpage` page class that does NOT auto-link:

```python
@register_page_class('subpage')
class SubPage(Page):
    """
    A page designed for tree-structure URLs.
    Does not create a global link - found by parent traversal.
    """

    @classmethod
    def auto_link_name(cls) -> bool:
        return False  # Does NOT auto-create global link

    @classmethod
    def allow_null_names(cls) -> bool:
        return False  # Must have name for URL building

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        return True  # Same name OK under different parents
```

### URL Resolution

The URL parser needs updating to handle subpages:

```python
def resolve_url(path: str) -> Optional[int]:
    """
    Resolve a URL path to a page ID.

    Examples:
    - 'alice' -> Look up link='alice'
    - 'alice/projects/proj1' -> Look up link='alice',
      then child named 'projects', then child named 'proj1'
    """
    parts = path.split('/')

    # First segment uses global link
    first = parts[0]
    page = get_page_by_link(first)
    if not page:
        return None

    # Remaining segments traverse children by name
    for segment in parts[1:]:
        child = get_child_by_name(page.id, segment)
        if not child:
            return None
        page = child

    return page.id
```

### Benefits

- **User spaces**: `/alice/projects/`, `/alice/blog/`, etc.
- **Documentation structure**: `/docs/install/`, `/docs/config/`, etc.
- **No namespace pollution**: `projects` under alice doesn't block `projects` as a top-level link
- **Natural hierarchy**: Matches mental model of folders/subfolders

---

## Module Structure

### Verification as Optional Modules

The verification system is implemented as peer modules alongside `hh/`:

```
project-root/
├── hh/                     # Core framework (never modified)
├── ext/                    # Configuration only
│   └── deploy/
│       └── conf/
│           ├── module_blacklist.py
│           └── verified_config.py
│
├── verified-core/          # Base verification (required for others)
│   ├── manifest.py
│   ├── page/
│   │   ├── __init__.py
│   │   ├── user.py         # UserPage class
│   │   ├── group.py        # GroupPage class
│   │   ├── company.py      # CompanyPage class
│   │   └── subpage.py      # SubPage class
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── credential.py   # Credential management
│   │   ├── magic_link.py   # Magic link generation/validation
│   │   └── session.py      # Session management
│   ├── permission/
│   │   ├── __init__.py
│   │   └── check.py        # Permission checking functions
│   ├── group/
│   │   ├── __init__.py
│   │   └── subgroup.py     # Subgroup management
│   └── deploy/
│       └── db/
│           └── schema.sql  # User database schema
│
├── verified-contact/       # Contact form submissions
│   ├── manifest.py
│   ├── page/
│   │   └── contact_submission.py
│   ├── action/
│   │   └── contact_action.py
│   └── deploy/
│       └── db/
│           └── schema.sql  # contact_submissions table
│
├── verified-comments/      # Comments on pages
│   ├── manifest.py
│   ├── page/
│   │   └── user_comment.py
│   └── action/
│       └── comment_action.py
│
└── verified-tilde/         # ~ page management
    ├── manifest.py
    ├── action/
    │   ├── grant_tilde.py
    │   └── subgroup_management.py
    └── http/
        └── tilde_ui.py     # UI for managing ~ pages
```

### Module Dependencies

```
verified-core     <- Required by all others
    ↑
    ├── verified-contact   (can work without ~, just needs verified email)
    ├── verified-comments  (needs edit access to pages)
    └── verified-tilde     (needs verified-core for user/group pages)
```

### Blacklisting Modules

Operators who don't want certain features can blacklist modules:

```python
# ext/deploy/conf/module_blacklist.py
MODULE_BLACKLIST = [
    'verified-comments',    # No user comments
    'verified-tilde',       # No ~ pages
]
# verified-core and verified-contact still active
```

---

## Authentication Flow

### Magic Link Flow

```
1. User enters email on login form
   POST /auth/magic-link
   Body: { "email": "alice@example.com" }

2. System creates/finds credential
   - Check credentials table for this email
   - If not exists: INSERT new credential (unverified)
   - If exists: use existing

3. Generate magic link token
   - token = secure_random(32 bytes, hex encoded)
   - expires_ts = NOW() + 15 minutes
   - INSERT INTO magic_links (token, credential_id, ...)

4. Send email
   - Email contains: https://example.com/auth/verify?token=abc123
   - Subject: "Your login link for Example Site"

5. User clicks link
   GET /auth/verify?token=abc123

6. Validate token
   - SELECT * FROM magic_links WHERE token = ? AND expires_ts > NOW() AND used_ts IS NULL
   - If not found: error "Link expired or invalid"
   - If found: UPDATE magic_links SET used_ts = NOW()

7. Update credential verification
   - UPDATE credentials SET verified_ts = NOW(), last_active_ts = NOW()

8. Create session
   - session_id = secure_random(32 bytes, hex encoded)
   - expires_ts = NOW() + 24 hours (configurable)
   - INSERT INTO sessions (session_id, credential_id, ...)

9. Set cookie and redirect
   - Set-Cookie: session=abc123; HttpOnly; Secure; SameSite=Strict
   - Redirect to intended destination or home
```

### Session Validation

```python
def get_current_credential(request) -> Optional[int]:
    """
    Get credential ID from session cookie.
    Returns None if not authenticated.
    """
    session_id = request.cookies.get('session')
    if not session_id:
        return None

    row = user_db.fetchone("""
        SELECT s.credential_id
        FROM sessions s
        WHERE s.session_id = %s
        AND s.expires_ts > NOW()
    """, (session_id,))

    if row:
        # Update last_active
        user_db.execute("""
            UPDATE sessions SET last_active_ts = NOW() WHERE session_id = %s
        """, (session_id,))
        return row[0]

    return None
```

### OAuth Flow (Future)

OAuth follows similar pattern:
1. Redirect to provider (Google, GitHub, etc.)
2. Callback with auth code
3. Exchange code for user info
4. Create/find credential with `credential_type='oauth_google'`, `credential_value=oauth_user_id`
5. Mark verified, create session

---

## MCP Tools

### Core Tools (verified-core)

```python
# Credential Management
@register_mcp_tool(tool_name='create_credential', tiers=[3, 4])
def create_credential(credential_type: str, credential_value: str) -> dict:
    """Create a new credential entry."""

@register_mcp_tool(tool_name='verify_credential', tiers=[3, 4])
def verify_credential(credential_id: int) -> dict:
    """Mark a credential as verified."""

@register_mcp_tool(tool_name='list_credentials', tiers=[3, 4])
def list_credentials(tilde_page_id: int = None) -> dict:
    """List credentials, optionally filtered by ~ page."""


# Subgroup Management
@register_mcp_tool(tool_name='create_subgroup_member', tiers=[3, 4])
def create_subgroup_member(owner_page_id: int, group_name: str, credential_id: int) -> dict:
    """Add a credential to a subgroup."""

@register_mcp_tool(tool_name='remove_subgroup_member', tiers=[3, 4])
def remove_subgroup_member(owner_page_id: int, group_name: str, credential_id: int) -> dict:
    """Remove a credential from a subgroup."""

@register_mcp_tool(tool_name='list_subgroup_members', tiers=[3, 4])
def list_subgroup_members(owner_page_id: int, group_name: str) -> dict:
    """List all credentials in a subgroup."""


# Ownership Management
@register_mcp_tool(tool_name='set_page_ownership', tiers=[3, 4])
def set_page_ownership(page_id: int, subgroup_ids: List[int]) -> dict:
    """Set ownership of a page to specific subgroups."""

@register_mcp_tool(tool_name='add_page_owner', tiers=[3, 4])
def add_page_owner(page_id: int, subgroup_id: int) -> dict:
    """Add a subgroup to page ownership."""

@register_mcp_tool(tool_name='remove_page_owner', tiers=[3, 4])
def remove_page_owner(page_id: int, subgroup_id: int) -> dict:
    """Remove a subgroup from page ownership."""

@register_mcp_tool(tool_name='get_page_owners', tiers=[3, 4])
def get_page_owners(page_id: int) -> dict:
    """Get all subgroups that own a page."""


# Permission Checking
@register_mcp_tool(tool_name='check_page_access', tiers=[3, 4])
def check_page_access(credential_id: int, page_id: int) -> dict:
    """Check if credential can edit a page."""
```

### Tilde Management Tools (verified-tilde)

```python
@register_mcp_tool(tool_name='grant_tilde_page', tiers=[3, 4])
def grant_tilde_page(credential_id: int, username: str, parent_page_id: int = None) -> dict:
    """
    Grant a ~ page to a verified credential.

    Creates UserPage, links credential, creates self-group, sets ownership.
    """

@register_mcp_tool(tool_name='revoke_tilde_page', tiers=[3, 4])
def revoke_tilde_page(tilde_page_id: int) -> dict:
    """
    Revoke a user's ~ page.

    Unlinks credentials, removes subgroups, optionally archives page.
    """

@register_mcp_tool(tool_name='transfer_tilde_ownership', tiers=[3, 4])
def transfer_tilde_ownership(tilde_page_id: int, new_credential_id: int) -> dict:
    """
    Transfer ~ page ownership to a different credential.

    Useful for the "orphan node" case (M.C. Escher's estate claims his page).
    """
```

---

## Implementation Phases

### Phase 1: Foundation (verified-core)

**Goal**: User database exists, credentials work, basic permission checking.

**Deliverables**:
- User database schema deployed
- Connection routing for user DB
- credentials table CRUD
- subgroups table CRUD
- page_owners table CRUD
- Basic permission check function (can_edit_page)
- MCP tools for credential/subgroup/ownership management

**Validation**: Admin can create credentials, subgroups, and ownership entries via MCP. Permission checks return correct YES/NO.

### Phase 2: Page Classes

**Goal**: UserPage, GroupPage, CompanyPage, SubPage classes working.

**Deliverables**:
- Page class implementations with correct validation methods
- Registration with page class registry
- Metadata extraction for user-specific fields
- SubPage class for tree URLs
- URL resolution updated for subpage traversal

**Validation**: Can create user/group pages via MCP. SubPage URLs resolve correctly.

### Phase 3: Authentication

**Goal**: Magic link authentication working end-to-end.

**Deliverables**:
- Magic link generation
- Email sending (SMTP integration)
- Token validation
- Session creation
- Session cookie handling
- Logout functionality

**Validation**: User can enter email, receive magic link, click it, and be logged in with valid session.

### Phase 4: Contact Forms (verified-contact)

**Goal**: Guests can submit contact forms after email verification.

**Deliverables**:
- contact_submissions table
- ContactSubmission page class (or just table-based)
- Contact form UI
- Submission list for admin review
- Reply functionality

**Validation**: Guest verifies email, submits message, admin sees it and can reply.

### Phase 5: User Interface

**Goal**: Web UI for verified users to manage their content.

**Deliverables**:
- Login/logout UI
- Profile editing for ~ users
- Subgroup management UI (for ~ users)
- "My content" view showing pages user owns

**Validation**: Logged-in user can edit their profile, manage their subgroups.

### Phase 6: Comments (verified-comments)

**Goal**: Verified users can comment on pages.

**Deliverables**:
- UserComment page class
- Comment form on pages
- Comment moderation for page owners
- Comment display at bottom of pages

**Validation**: Verified user can add comment to page they have access to. Page owner can approve/delete.

### Phase 7: Polish and Scale

**Goal**: Production-ready verification system.

**Deliverables**:
- Session cleanup cron job
- Magic link cleanup cron job
- Rate limiting on auth endpoints
- Abuse prevention (lockouts, etc.)
- Documentation for operators
- Configuration options for enabling/disabling features

**Validation**: System handles abuse scenarios gracefully. Documentation complete.

---

## Examples and Use Cases

### Use Case 1: Public Puzzle Database

**Scenario**: A puzzle enthusiast runs a Henhouse instance cataloging wooden puzzles. They want collectors to be able to add their own photos and notes.

**Setup**:
1. Admin creates `/puzzles` hierarchy with designs, instances
2. Admin sets ownership of `/puzzles` to `admins/admins`
3. Admin creates `collectors` group page
4. Collectors verify email, admin adds them to `collectors/collectors` subgroup
5. Admin sets certain instance pages to be owned by `collectors/collectors`

**Usage**:
- Collector logs in with magic link
- Browses to `/puzzles/some-design/instance-42`
- Adds their photo and notes (can edit because in owning group)
- Cannot delete others' photos (not owner of those media files)

### Use Case 2: Documentation with Community Contributions

**Scenario**: An open-source project uses Henhouse for docs. They want trusted contributors to edit directly.

**Setup**:
1. Main docs at `/docs` owned by `maintainers/maintainers`
2. Community section at `/docs/community` owned by `contributors/contributors`
3. Interested users verify email, request contributor access
4. Maintainer adds them to contributors group

**Usage**:
- Contributors can edit anything under `/docs/community`
- Cannot edit main docs (not in maintainers group)
- Maintainers can edit everything (parent chain access)

### Use Case 3: Artist Portfolio with Estate Control

**Scenario**: A site documents artists' work. Some artists are deceased but their estates may want control.

**Setup**:
1. `/artists/escher` exists, owned by `admins/admins` (orphan pattern)
2. Escher Foundation contacts admin requesting control
3. Admin creates credential for foundation
4. Admin creates `escher_foundation` user page
5. Admin transfers ownership of `/artists/escher` to `escher_foundation/escher_foundation`

**Usage**:
- Foundation can now edit Escher's page and children
- Can moderate any user contributions under the page
- Admin can still override if needed (parent chain)

### Use Case 4: Multi-Tenant Business Accounts

**Scenario**: A SaaS uses Henhouse for customer portals. Each customer has a company account with multiple employees.

**Setup**:
1. Each customer gets a CompanyPage: `/customers/acme`
2. Company has subgroups: `acme/admins`, `acme/users`
3. Multiple credentials linked to different subgroups

**Usage**:
- Acme admins can manage their entire `/customers/acme` subtree
- Acme users can edit only pages specifically owned by `acme/users`
- SaaS admin (root tier) can access everything

---

## Integration with Existing Systems

### Tier System Integration

The verification system operates at tier 2. Higher tiers bypass it:

```python
def check_crud_access(gateway, page_id: int) -> bool:
    """
    Check if current user can perform CRUD on page.

    Tier 3/4: Always allowed (admin/root)
    Tier 2: Check verification system
    Tier 1: Never allowed (guest)
    """
    tier = gateway._user_tier_level

    if tier >= 3:
        return True  # Admin/root always allowed

    if tier == 2:
        credential_id = get_credential_from_session(gateway.request)
        if credential_id:
            return can_edit_page(credential_id, page_id)
        return False

    return False  # Guest not allowed
```

### MCP Integration

MCP requests at tier 2 need credential context:

```python
# In MCP request handling
def handle_mcp_request(request, gateway):
    if gateway._user_tier_level == 2:
        # Get credential from session/header
        credential_id = get_credential_from_request(request)
        if not credential_id:
            return error_response("Authentication required")
        gateway._verified_credential_id = credential_id
```

### Flask Integration

The Flask app needs session middleware:

```python
@app.before_request
def load_verified_session():
    """Load verified user session if present."""
    if current_tier() == 2:
        credential_id = get_current_credential(request)
        if credential_id:
            g.verified_credential_id = credential_id
            g.verified_tilde_page_id = get_tilde_page_id(credential_id)
```

### Cache Considerations

The verification system intentionally does NOT cache permission checks:

- Fresh check every CRUD operation
- No stale permissions after group changes
- Simple to reason about
- Performance is acceptable for tier-2 volume

If performance becomes an issue, consider:
- Caching at the session level (clear on group change)
- Denormalized "can_edit" column (complex to maintain)
- Read-through cache with short TTL

---

## Future Considerations

### OAuth Providers

Currently magic link only. Future:
- Google OAuth
- GitHub OAuth
- Custom OAuth providers

Implementation: Same credential pattern, different `credential_type`.

### Read-Only Access

Current model is binary: can edit or can't. Future:
- `page_viewers` table for read-only access
- Check viewers for protected pages

### Rate Limiting

Not implemented in core. Future:
- Per-credential rate limits
- Per-IP rate limits for anonymous endpoints
- Lockout after failed attempts

### Notification System

Future addition:
- Email notifications for page changes
- Webhook notifications for integrations
- Per-user notification preferences

### Audit Log

The history database (separate project) would capture:
- All CRUD operations with credential_id
- Permission check results
- Ownership changes

### Federation

Far future:
- Trust relationships between Henhouse instances
- Cross-instance user verification
- Shared credential verification

---

## Summary

The Tier 2 Verification System provides:

1. **Users as pages** - UserPage, GroupPage, CompanyPage share the page hierarchy
2. **Separate user database** - Clean separation, no main schema changes
3. **Subgroups as keystone** - Single table linking credentials to groups
4. **Lazy permission checking** - Walk up parent chain, first YES wins
5. **Top-down ownership** - Parents always control children
6. **Media direct ownership** - No hierarchy, owner only can delete
7. **Multiple credentials** - Email + OAuth linked to same identity
8. **Modular implementation** - Core + optional contact/comments/tilde modules

The system is designed to be:
- **Optional** - Blacklist modules you don't want
- **Scalable** - User DB can move to separate host
- **Simple** - YES/NO permission model, no complex ACLs
- **Extensible** - Add new page types, new auth methods as needed
