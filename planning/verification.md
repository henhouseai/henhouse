# Tier 2 Verification System

This document covers the planned implementation of the Tier 2 (verified) authentication and authorization system using magic links, OAuth, and database-backed sessions. This system allows guest users (Tier 1) to elevate to verified status (Tier 2) through email-based or OAuth-based authentication, enabling them to perform CRUD operations through a maintenance job queue system.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [Database Schema](#3-database-schema)
4. [User Accounts as Page-Derived Classes](#4-user-accounts-as-page-derived-classes)
5. [Authentication Methods](#5-authentication-methods)
6. [Session Management](#6-session-management)
7. [Page Ownership System](#7-page-ownership-system)
8. [Maintenance Queue for CRUD Operations](#8-maintenance-queue-for-crud-operations)
9. [Permission System](#9-permission-system)
10. [Implementation Plan](#10-implementation-plan)
11. [Integration Points](#11-integration-points)

## Agent Quick Reference

- **Purpose**: Allow Tier 1 (guest) users to elevate to Tier 2 (verified) via magic links or OAuth, enabling CRUD operations through maintenance queue
- **User Model**: Users are page-derived classes (`class='user'`), inheriting all Page CRUD functionality
- **Authentication**: Magic Links (email) and OAuth (Google, GitHub, Apple, X) - no password storage
- **Auth Tokens**: Stored in separate `user_auth_tokens` table (not in metadata - too private)
- **Sessions**: Database-backed sessions for verified tier only (admin/root use subdomain/SSH, not sessions)
- **Ownership**: Simple boolean ownership via `page_owners` table (no priorities, multiple owners allowed)
- **CRUD Operations**: All verified user CRUD goes through maintenance queue → daemon checks ownership → executes or sets `pending_review`
- **Whitelisting**: Uses existing `@register_maintenance_tool` decorator system for job type whitelisting
- **Flow**: Authenticate → Get user page ID → Enqueue maintenance job → Daemon processes → Check ownership → Execute or review

## Agent Training Notes

### Tier System Context
- **Tier 1 (Guest)**: Default, read-only, no authentication required
- **Tier 2 (Verified)**: Elevated via magic link/OAuth, authenticated user with user page, can enqueue maintenance jobs
- **Tier 3 (Admin)**: HTTP Basic Auth on `admin.{domain}` subdomain, processes maintenance queue, assigns ownership
- **Tier 4 (Root)**: HTTP Basic Auth on `panel.{domain}` subdomain or SSH with credential file in home directory

### Current State
- Tier 1, 3, 4 are working (static tier per instance)
- Tier 2 does not exist yet
- No session management currently implemented
- No user accounts or ownership system
- Maintenance daemon exists but only processes admin-initiated jobs
- Tier determined by instance configuration

### Design Principles
- **No Password Storage**: Magic links and OAuth only - no passwords ever stored
- **Page-Derived Users**: Leverage existing Page infrastructure for user accounts
- **Simple Ownership**: Boolean ownership (owned or not), no priority levels
- **Maintenance Queue**: All verified user CRUD goes through queue for ownership checks
- **Decorator-Based Whitelisting**: Use existing `@register_maintenance_tool` system
- **General-Purpose**: System designed for any use case, not puzzle-specific
- **Manual Ownership Claims**: Guild handles ownership assignment via email/admin panel, no public-facing claim button

---

## 1. System Overview

The Tier 2 verification system enables dynamic tier elevation from guest (Tier 1) to verified (Tier 2) status. Unlike Tiers 3 and 4 which use static subdomain-based authentication, Tier 2 requires session-based authentication that can be initiated from the main guest site.

### Architecture Flow

```
Guest User (Tier 1)
    ↓
Authenticate (Magic Link or OAuth)
    ↓
User Page Created/Retrieved (class='user')
    ↓
Session Created in DB → Cookie Set → Tier Elevated to 2
    ↓
Verified User (Tier 2)
    ↓
MCP Request → Enqueue Maintenance Job (job_type, payload_json, requested_by_page_id, target_page_id)
    ↓
Maintenance Daemon (Admin Tier)
    ↓
Check Ownership → Check Whitelist → Execute or Set pending_review
    ↓
User Checks Job Status (via MCP)
```

### Key Components

- **Authentication System**: Magic links (email) and OAuth (Google, GitHub, Apple, X)
- **User Accounts**: Page-derived classes (`class='user'`), inheriting Page CRUD functionality
- **Session System**: Database-backed sessions with cookie-based session_id (verified tier only)
- **Page Ownership**: Simple boolean ownership via `page_owners` table
- **Maintenance Queue**: Job queue system for verified user CRUD operations
- **Ownership Checks**: Business logic layer checking ownership before executing operations
- **Whitelisting**: Decorator-based system using `@register_maintenance_tool`

---

## 2. Architecture Principles

### User Accounts as Page-Derived Classes

**Core Principle**: Users are not stored in a separate `users` table. Instead, users are pages with `class='user'`, leveraging the existing Page infrastructure:

- **Page ID = User ID**: Each user account has a unique page ID
- **Inheritance**: Users inherit all Page functionality (CRUD, media attachments, subpages, etc.)
- **Metadata**: Public user information stored in `pages.metadata` JSON column
- **Auth Tokens**: Private authentication tokens stored in separate `user_auth_tokens` table (not metadata)

**User Hierarchy**:
- `Page` (base class)
  - `User` (`class='user'`)
    - `Person` (`class='person'`) - Individual users
    - `Company` (`class='company'`) - Organizational users

**Relational Links** (not ownership):
- Users can be linked to designs, production runs, collected instances, items for sale
- Multiple users can be designers/manufacturers/collectors/retailers for the same item
- These are relational database links, separate from ownership
- Ownership determines editing rights; relational links determine attribution/display

### Authentication Methods

**Magic Links**:
- Email-based verification
- No password storage
- One-time token system
- Suitable for guest accounts or recurring users

**OAuth Providers**:
- Google
- GitHub
- Apple
- X (Twitter)
- No password storage
- Suitable for recurring users

**Token Storage**:
- Auth tokens stored in `user_auth_tokens` table (separate from sessions)
- Not stored in `pages.metadata` (too private, metadata is publicly visible)
- Multiple tokens per user (email + multiple OAuth providers)

### Session Management

**Sessions are for Verified Tier Only**:
- Guest tier: No sessions needed
- Verified tier: Database-backed sessions with cookie-based session_id
- Admin/Root tiers: Use subdomain HTTP Basic Auth or SSH with credential files, not sessions

**Session Flow**:
- Session created after successful authentication
- Cookie stores `session_id` only
- Session lookup determines tier (defaults to tier 1 if no session)
- Session contains `user_page_id` (the user's page ID)

### Page Ownership System

**Simple Boolean Ownership**:
- No priority levels
- Multiple owners allowed
- Either you own it or you don't

**Ownership Table**: `page_owners`
- Links `page_id` to `owner_page_id` (user's page ID)
- Many-to-many relationship (multiple owners per page)

**Ownership Inheritance**:
- Ownership flows down hierarchically from parent to child pages
- Explicit ownership overrides inheritance
- New pages created by verified users are automatically owned by creator
- Once a branch is overridden, it becomes the new inheritance point down the tree

**Ownership Claims**:
- Manual process only (no public-facing "Claim Ownership" button)
- Guild handles ownership assignment via email or admin panel
- For puzzle database: Guild members can claim ownership of their designs/production runs
- Dead/inactive users: Trusted experts can be assigned ownership to maintain pages

**Ownership vs. Attribution**:
- Ownership determines editing rights
- Attribution (designer/manufacturer/collector) is separate relational data
- A user can be a designer without owning the page (if dead/inactive)
- A trusted expert can own pages for a dead artisan

### Maintenance Queue for CRUD Operations

**All Verified User CRUD Goes Through Queue**:
- Verified users cannot directly modify database
- All operations enqueued as maintenance jobs
- Maintenance daemon (running at Admin tier) processes jobs
- Daemon checks ownership before executing

**Job Structure**:
- `job_type`: Name of maintenance tool (must be whitelisted)
- `payload_json`: JSON payload with operation parameters
- `requested_by_page_id`: User's page ID (who made the request)
- `target_page_id`: Page being modified (for ownership checks)
- `status`: `pending`, `processing`, `completed`, `failed`, `pending_review`

**Whitelisting**:
- Uses existing `@register_maintenance_tool` decorator system
- Only whitelisted job types can be enqueued by verified users
- Prevents arbitrary command execution
- Examples: `edit_page_text`, `upload_image`, `modify_image_caption`, etc.

**Processing Flow**:
1. Verified user makes MCP request (via web browser)
2. MCP handler enqueues maintenance job with `status='pending'`
3. Maintenance daemon claims job
4. Daemon checks ownership (`requested_by_page_id` vs `target_page_id`)
5. If owned: Execute operation, set `status='completed'`
6. If not owned: Set `status='pending_review'` for agent/human review
7. User checks job status via MCP (can poll for completion)

**Job Status Checking**:
- Users can check job status via MCP calls
- MCP protocol supports async tasks with status tokens (new feature)
- Users don't have to wait for completion, can poll status

### Permission System

**Two-Layer Permission System**:

**Layer 1: Database Permissions (MySQL Grants)**:
- Guest tier: Read-only access
- Verified tier: INSERT on `maintenance_jobs`, SELECT on `maintenance_jobs` (own jobs)
- Admin tier: Full access to process queue, assign ownership
- Root tier: Full system access

**Layer 2: Business Logic Permissions**:
- Ownership checks before executing operations
- Whitelist checks for allowed job types
- Verification level checks (must be Tier 2 to enqueue jobs)

**Ownership Check Logic**:
- Check if `requested_by_page_id` owns `target_page_id` (explicit ownership)
- If not explicit, check parent ownership (inheritance)
- If owned: Execute operation
- If not owned: Set `pending_review` for review

**Review Process**:
- Initially: Manual human review (Guild admin)
- Future: Agent curator loop (when CLI agent daemon is implemented)
- Review decides whether to approve or reject
- Approved jobs get executed, rejected jobs get `status='failed'` with reason

---

## 3. Database Schema

### user_auth_tokens Table

Stores authentication tokens for users (email addresses and OAuth tokens). Separate from sessions and metadata.

```sql
CREATE TABLE user_auth_tokens (
    token_id INT AUTO_INCREMENT PRIMARY KEY,
    user_page_id INT NOT NULL,
    token_type ENUM('email', 'oauth_google', 'oauth_github', 'oauth_apple', 'oauth_x') NOT NULL,
    token_value VARCHAR(255) NOT NULL,
    oauth_provider_id VARCHAR(255) NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME NULL,
    INDEX idx_user_page_id (user_page_id),
    INDEX idx_token_type_value (token_type, token_value),
    INDEX idx_oauth_provider (oauth_provider_id),
    FOREIGN KEY (user_page_id) REFERENCES pages(page_id) ON DELETE CASCADE
);
```

**Fields**:
- `token_id`: Primary key
- `user_page_id`: Foreign key to `pages.page_id` (the user's page)
- `token_type`: Type of token (email address or OAuth provider)
- `token_value`: The actual token (email address or OAuth user ID)
- `oauth_provider_id`: OAuth provider's user ID (for OAuth tokens)
- `verified`: Whether this token has been verified (email verification, OAuth callback)
- `created_at`: When token was created
- `last_used_at`: Last time token was used for authentication

**Permissions**:
- Guest tier: INSERT (for creating tokens during registration)
- Verified tier: SELECT, UPDATE (for own tokens)
- Admin tier: Full access (for management)

### sessions Table

Stores active user sessions for verified tier only. Admin/Root tiers use subdomain/SSH authentication, not sessions.

```sql
CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_page_id INT NOT NULL,
    tier INT NOT NULL DEFAULT 2,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_page_id (user_page_id),
    INDEX idx_expires (expires_at),
    INDEX idx_last_activity (last_activity),
    FOREIGN KEY (user_page_id) REFERENCES pages(page_id) ON DELETE CASCADE
);
```

**Fields**:
- `session_id`: Unique session identifier (stored in cookie, cryptographically secure)
- `user_page_id`: Foreign key to `pages.page_id` (the user's page)
- `tier`: User's tier level (always 2 for verified)
- `created_at`: Session creation timestamp
- `expires_at`: Session expiration (typically 30 days)
- `last_activity`: Last request timestamp (for cleanup and sliding expiration)

**Permissions**:
- Guest tier: INSERT (creates session after authentication)
- Verified tier: SELECT, UPDATE (refresh own session)
- Admin tier: SELECT, DELETE (for session management)

### page_owners Table

Stores page ownership relationships. Simple boolean ownership (no priorities).

```sql
CREATE TABLE page_owners (
    page_id INT NOT NULL,
    owner_page_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by_page_id INT NULL,
    PRIMARY KEY (page_id, owner_page_id),
    INDEX idx_owner_page_id (owner_page_id),
    INDEX idx_page_id (page_id),
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    FOREIGN KEY (owner_page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_page_id) REFERENCES pages(page_id) ON DELETE SET NULL
);
```

**Fields**:
- `page_id`: The page being owned
- `owner_page_id`: The user's page ID (the owner)
- `created_at`: When ownership was assigned
- `created_by_page_id`: Who assigned the ownership (admin/user, for audit)

**Permissions**:
- Guest tier: No access
- Verified tier: SELECT (can check ownership)
- Admin tier: INSERT, DELETE (can assign/revoke ownership)
- Root tier: Full access

**Ownership Logic**:
- Multiple owners allowed (composite primary key)
- Explicit ownership overrides inheritance
- New pages created by verified users automatically get ownership entry
- Ownership flows down hierarchically unless overridden

### magic_links Table

Stores one-time magic link tokens for email verification.

```sql
CREATE TABLE magic_links (
    token VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_expires (expires_at)
);
```

**Fields**:
- `token`: Cryptographically secure random token (64 chars)
- `email`: User's email address
- `expires_at`: Token expiration (typically 15 minutes)
- `used`: Boolean flag to prevent reuse
- `created_at`: Timestamp for audit

**Permissions**:
- Guest tier: INSERT, SELECT, UPDATE (for validation)
- Other tiers: No access needed

### maintenance_jobs Table (Enhanced)

Existing `maintenance_jobs` table enhanced with ownership tracking fields.

```sql
-- Existing fields (assumed):
-- job_id, job_type, payload_json, status, created_at, claimed_at, completed_at, error_message

-- New fields to add:
ALTER TABLE maintenance_jobs
ADD COLUMN requested_by_page_id INT NULL,
ADD COLUMN target_page_id INT NULL,
ADD INDEX idx_requested_by (requested_by_page_id),
ADD INDEX idx_target_page (target_page_id),
ADD INDEX idx_status_requested (status, requested_by_page_id),
ADD FOREIGN KEY (requested_by_page_id) REFERENCES pages(page_id) ON DELETE SET NULL,
ADD FOREIGN KEY (target_page_id) REFERENCES pages(page_id) ON DELETE SET NULL;
```

**New Fields**:
- `requested_by_page_id`: User's page ID who enqueued the job
- `target_page_id`: Page being modified (for ownership checks)

**Permissions**:
- Guest tier: No access
- Verified tier: INSERT (enqueue jobs), SELECT (own jobs only)
- Admin tier: SELECT, UPDATE, DELETE (process queue)
- Root tier: Full access

---

## 4. User Accounts as Page-Derived Classes

### User Page Structure

Users are pages with `class='user'`:

```python
# User page metadata structure (in pages.metadata JSON)
{
    "display_name": "John Doe",
    "bio": "Puzzle designer and collector",
    "public_email": "john@example.com",  # Optional, public-facing
    "website": "https://johndoe.com",
    "location": "Portland, OR",
    # ... other public profile information
}
```

**Key Points**:
- User page ID = User account ID
- All Page CRUD operations work on user pages
- Users can attach images, files, audio, video to their profile
- Users can create subpages (e.g., blog posts, portfolio items)
- Public information in metadata, private auth tokens in separate table

### User Hierarchy

**Base User** (`class='user'`):
- Generic user account
- Can be person or company

**Person** (`class='person'`):
- Derived from User
- Individual user account
- Additional metadata: birthdate, etc.

**Company** (`class='company'`):
- Derived from User
- Organizational account
- Additional metadata: tax ID, etc.

**Implementation**:
- Use existing Page class system
- `class` field determines user type
- Can add derived classes via `@register_page_class` decorator
- All inherit Page functionality automatically

### Relational Links (Not Ownership)

**Designer/Manufacturer/Collector/Retailer Links**:
- Separate relational tables linking users to content
- `design_designers`: Links users to puzzle designs (many-to-many)
- `production_manufacturers`: Links users to production runs (many-to-many)
- `collection_collectors`: Links users to collected instances (many-to-many)
- `sale_retailers`: Links users to items for sale (many-to-many)

**Purpose**:
- Attribution and display (who designed/manufactured/collects/sells what)
- Separate from ownership (editing rights)
- Multiple users can be linked to same item
- Dead/inactive users can still be linked (historical record)

**Example**:
- User A (dead designer) designed Puzzle X
- User B (trusted expert) owns Puzzle X pages (can edit)
- Both User A and User B are linked as designers (attribution)
- User B's ownership gives editing rights, User A's link gives credit

---

## 5. Authentication Methods

### Magic Links

**Flow**:
1. User provides email address
2. System generates cryptographically secure token
3. Token stored in `magic_links` table with expiration
4. Email sent with verification link
5. User clicks link → Token validated → User page created/retrieved → Session created

**Token Security**:
- Use `secrets.token_urlsafe(64)` for token generation
- One-time use (marked as `used` after validation)
- Expiration enforced (typically 15 minutes)
- Rate limiting to prevent abuse

**Email Handling**:
- Don't reveal if email exists (prevent enumeration)
- Generic success messages
- Log email send failures for monitoring

### OAuth Providers

**Supported Providers**:
- Google (`oauth_google`)
- GitHub (`oauth_github`)
- Apple (`oauth_apple`)
- X/Twitter (`oauth_x`)

**Flow**:
1. User clicks "Sign in with [Provider]"
2. Redirect to OAuth provider
3. User authorizes application
4. OAuth callback with authorization code
5. Exchange code for access token and user info
6. Look up or create user page based on OAuth user ID
7. Store OAuth token in `user_auth_tokens` table
8. Create session

**Token Storage**:
- OAuth provider user ID stored in `user_auth_tokens.token_value`
- OAuth provider ID stored in `user_auth_tokens.oauth_provider_id`
- Access tokens stored securely (encrypted or in secure storage)
- Multiple OAuth providers per user allowed

**User Matching**:
- First, check if `user_auth_tokens` has matching OAuth token
- If found, use existing `user_page_id`
- If not found, check if email matches existing user
- If email matches, link OAuth token to existing user
- If no match, create new user page

### Authentication Token Management

**Multiple Tokens Per User**:
- One email token (for magic links)
- Multiple OAuth tokens (one per provider)
- All stored in `user_auth_tokens` table
- User can authenticate via any verified token

**Token Verification**:
- Email tokens: Verified via magic link click
- OAuth tokens: Verified via OAuth callback
- `verified` flag tracks verification status
- Only verified tokens can be used for authentication

**Token Privacy**:
- Tokens stored in separate table (not metadata)
- Metadata is publicly visible, tokens are private
- Sessions are separate from tokens (tokens for auth, sessions for state)

---

## 6. Session Management

### Session Creation

**After Successful Authentication**:
1. User authenticates (magic link or OAuth)
2. User page created/retrieved
3. Generate cryptographically secure `session_id`
4. Calculate expiration (typically 30 days)
5. INSERT into `sessions` table:
   - `session_id`: Secure random token
   - `user_page_id`: User's page ID
   - `tier`: 2 (verified)
   - `expires_at`: 30 days from now
6. Set cookie with `session_id`
7. Redirect to verified content area

### Session Usage

**On Every Request**:
1. Flask reads `session_id` from cookie
2. SELECT from `sessions` WHERE `session_id = ?` AND `expires_at > NOW()`
3. If found:
   - Get `user_page_id` and `tier` from session
   - Update `last_activity` timestamp
   - Use tier for Gateway credential loading
   - Pass `user_page_id` to request handlers
4. If not found/expired:
   - Clear cookie
   - Default to tier 1 (guest)

**Session Refresh**:
- Update `last_activity` on each request
- Optionally extend `expires_at` on activity (sliding expiration)
- Cleanup expired sessions via cron job

### Session Security

**Cookie Configuration**:
- `HttpOnly`: Prevents JavaScript access
- `Secure`: HTTPS only
- `SameSite`: CSRF protection
- `session_id` must be cryptographically secure

**Session Fixation Protection**:
- Regenerate `session_id` after authentication
- Invalidate old sessions on password change (if passwords existed)

### Admin/Root Tier Sessions

**No Sessions for Admin/Root**:
- Admin tier: HTTP Basic Auth on `admin.{domain}` subdomain
- Root tier: HTTP Basic Auth on `panel.{domain}` subdomain or SSH with credential file
- Sessions are only for verified tier (dynamic elevation from guest)

---

## 7. Page Ownership System

### Ownership Table Structure

**`page_owners` Table**:
- Links `page_id` to `owner_page_id` (user's page ID)
- Many-to-many relationship (multiple owners per page)
- Simple boolean ownership (no priority levels)

### Ownership Inheritance

**Hierarchical Flow**:
- Ownership flows down from parent to child pages
- If parent is owned, children inherit ownership unless explicitly overridden
- Explicit ownership entry overrides inheritance
- Once a branch is overridden, it becomes the new inheritance point down the tree

**Example**:
```
Page 1 (owned by User A)
  └─ Page 2 (inherits from Page 1, owned by User A)
      └─ Page 3 (explicitly owned by User B, overrides inheritance)
          └─ Page 4 (inherits from Page 3, owned by User B)
```

**Automatic Ownership**:
- When verified user creates a page, they automatically own it
- Ownership entry created in `page_owners` table
- `created_by_page_id` set to creator's page ID

### Ownership Checks

**Check Logic**:
1. Check explicit ownership: `SELECT * FROM page_owners WHERE page_id = ? AND owner_page_id = ?`
2. If not found, check parent ownership (recursive up the tree)
3. If owned at any level: Return true
4. If not owned: Return false

**Implementation**:
```python
def check_page_ownership(page_id: int, user_page_id: int) -> bool:
    # Check explicit ownership
    if has_explicit_ownership(page_id, user_page_id):
        return True
    
    # Check parent ownership (recursive)
    parent_id = get_parent_page_id(page_id)
    if parent_id:
        return check_page_ownership(parent_id, user_page_id)
    
    return False
```

### Ownership Assignment

**Manual Process Only**:
- No public-facing "Claim Ownership" button
- Guild handles ownership assignment via email or admin panel
- For puzzle database: Guild members email to claim ownership
- Admin panel can assign/revoke ownership

**Ownership Claims**:
- User emails Guild: "I see my design on your system, I'd like to claim ownership"
- Guild verifies identity (known email, Guild membership)
- Guild admin assigns ownership via admin panel
- Ownership entry created in `page_owners` table

**Ownership Conflicts**:
- Guild decides if there's a conflict
- Guild can revoke ownership from both parties if needed
- Guild can assign ownership to one party over another
- Simple resolution: Guild has final say

### Ownership vs. Attribution

**Ownership**:
- Determines editing rights
- Stored in `page_owners` table
- Boolean (owned or not)

**Attribution**:
- Determines display/credit (who designed/manufactured/collects/sells)
- Stored in relational tables (separate from ownership)
- Many-to-many (multiple designers/manufacturers per item)

**Example**:
- User A (dead designer) designed Puzzle X → Attribution link
- User B (trusted expert) owns Puzzle X → Ownership entry
- User B can edit Puzzle X pages (ownership)
- User A gets credit as designer (attribution)
- Both can coexist

### Dead/Inactive Users

**Trusted Experts**:
- Dead/inactive users' pages can be owned by trusted experts
- Trusted expert maintains pages on behalf of dead artisan
- Ownership assigned by Guild
- Attribution links remain (historical record)

**Example**:
- Designer dies → Their designs remain in system
- Trusted collector becomes expert → Guild assigns ownership
- Expert maintains designer's pages
- Designer still linked as designer (attribution)

---

## 8. Maintenance Queue for CRUD Operations

### Job Structure

**Enhanced `maintenance_jobs` Table**:
- `job_id`: Primary key
- `job_type`: Name of maintenance tool (must be whitelisted)
- `payload_json`: JSON payload with operation parameters
- `requested_by_page_id`: User's page ID (who made the request)
- `target_page_id`: Page being modified (for ownership checks)
- `status`: `pending`, `processing`, `completed`, `failed`, `pending_review`
- `created_at`: When job was enqueued
- `claimed_at`: When daemon claimed job
- `completed_at`: When job completed
- `error_message`: Error details if failed

### Job Enqueueing

**From Verified User MCP Request**:
1. User makes MCP request via web browser (TypeScript `RPCClient`)
2. MCP handler receives request
3. Handler validates `job_type` is whitelisted (check `@register_maintenance_tool` decorators)
4. Handler extracts `target_page_id` from payload
5. Handler enqueues job:
   ```sql
   INSERT INTO maintenance_jobs (
       job_type,
       payload_json,
       requested_by_page_id,
       target_page_id,
       status
   ) VALUES (?, ?, ?, ?, 'pending')
   ```
6. Return job ID to user

**Whitelist Check**:
- Scan for `@register_maintenance_tool` decorators
- Build whitelist of allowed job types
- Only whitelisted types can be enqueued by verified users
- Prevents arbitrary command execution

**Example Whitelisted Job Types** (initial set):
- `edit_page_text`: Modify page text content
- `upload_image`: Upload new image
- `modify_image_caption`: Change image caption
- `add_subpage`: Create new subpage
- `modify_page_name`: Change page name
- More to be added as needed

### Job Processing

**Maintenance Daemon Flow**:
1. Daemon claims next `pending` job (optimistic locking)
2. Set `status='processing'`, `claimed_at=NOW()`
3. Extract `requested_by_page_id` and `target_page_id`
4. Check ownership: `check_page_ownership(target_page_id, requested_by_page_id)`
5. If owned:
   - Execute operation (call maintenance tool)
   - Set `status='completed'`, `completed_at=NOW()`
6. If not owned:
   - Set `status='pending_review'`
   - Log for review (manual or agent)

**Ownership Check**:
- Check explicit ownership first
- If not found, check parent ownership (inheritance)
- If owned: Execute
- If not owned: Set `pending_review`

**Error Handling**:
- If operation fails: Set `status='failed'`, `error_message=error_details`
- If ownership check fails: Set `status='pending_review'`
- User can check status via MCP

### Job Status Checking

**User Polling**:
- Users can check job status via MCP calls
- MCP protocol supports async tasks with status tokens (new feature)
- Users don't have to wait for completion
- Can poll status until `completed` or `failed`

**Status Values**:
- `pending`: Job enqueued, waiting for daemon
- `processing`: Daemon is working on it
- `completed`: Operation succeeded
- `failed`: Operation failed (check `error_message`)
- `pending_review`: Ownership check failed, awaiting review

**MCP Integration**:
- New MCP protocol feature: Tasks that can be started and checked later
- User gets job token/ID when enqueuing
- User can poll status with token/ID
- Status returned as JSON response

### Review Process

**Initial Implementation** (Manual):
- Jobs with `status='pending_review'` appear in admin panel
- Guild admin reviews request
- Admin checks ownership, user identity, request legitimacy
- Admin approves or rejects
- Approved: Execute operation, set `status='completed'`
- Rejected: Set `status='failed'`, `error_message='Rejected: reason'`

**Future Implementation** (Agent Curator):
- When CLI agent daemon is implemented
- Agent reviews `pending_review` jobs
- Agent checks ownership, user history, request patterns
- Agent approves or rejects based on rules
- Human fallback for edge cases

**Review Criteria**:
- Ownership check (does user own the page?)
- User verification level (are they verified?)
- Request legitimacy (does the request make sense?)
- Historical patterns (has user made similar requests before?)

---

## 9. Permission System

### Layer 1: Database Permissions (MySQL Grants)

**Guest Tier (Tier 1)**:
- SELECT on most tables (read-only)
- INSERT on `magic_links`, `sessions` (for authentication)
- No UPDATE or DELETE

**Verified Tier (Tier 2)**:
- SELECT on `sessions` (own sessions), `maintenance_jobs` (own jobs)
- UPDATE on `sessions` (refresh own session)
- INSERT on `maintenance_jobs` (enqueue jobs)
- SELECT on `page_owners` (check ownership)
- SELECT on `pages` (read pages)
- No direct UPDATE/DELETE on content tables

**Admin Tier (Tier 3)**:
- Full access to `maintenance_jobs` (process queue)
- INSERT, DELETE on `page_owners` (assign/revoke ownership)
- Full access to all content tables (for processing jobs)
- SELECT on `sessions` (session management)

**Root Tier (Tier 4)**:
- Full system access
- Can modify any table
- Can override any permission

### Layer 2: Business Logic Permissions

**Ownership Checks**:
- Before executing operation, check if `requested_by_page_id` owns `target_page_id`
- Check explicit ownership first
- If not found, check parent ownership (inheritance)
- If owned: Execute
- If not owned: Set `pending_review`

**Whitelist Checks**:
- Only `@register_maintenance_tool` decorated functions can be enqueued
- Prevents arbitrary command execution
- Whitelist built from decorator scanning

**Verification Level Checks**:
- Must be Tier 2 (verified) to enqueue jobs
- Session must be valid
- `user_page_id` must exist

**Operation-Specific Checks**:
- Some operations may have additional checks
- Example: `upload_image` may check file size limits
- Example: `add_subpage` may check parent page permissions
- These are implemented in individual maintenance tools

### Permission Flow

**Complete Flow**:
1. User makes MCP request (via web browser)
2. Flask middleware checks session → Gets `user_page_id` and `tier`
3. MCP handler checks `tier == 2` (verified)
4. MCP handler checks `job_type` is whitelisted
5. MCP handler enqueues job with `requested_by_page_id` and `target_page_id`
6. Maintenance daemon claims job
7. Daemon checks ownership (`requested_by_page_id` vs `target_page_id`)
8. If owned: Execute operation
9. If not owned: Set `pending_review`
10. User checks status via MCP

**Error Cases**:
- Not verified: Reject request (must be Tier 2)
- Job type not whitelisted: Reject request
- Ownership check fails: Set `pending_review`
- Operation fails: Set `status='failed'`, return error

---

## 10. Implementation Plan

### Phase 1: Database Setup

**Tasks**:
1. Create `user_auth_tokens` table
2. Create `sessions` table
3. Create `page_owners` table
4. Create `magic_links` table (if not exists)
5. Enhance `maintenance_jobs` table (add `requested_by_page_id`, `target_page_id`)
6. Grant permissions:
   - Guest tier: INSERT on `magic_links`, `sessions`, `user_auth_tokens`
   - Verified tier: INSERT/SELECT on `maintenance_jobs`, SELECT on `page_owners`, SELECT/UPDATE on `sessions`
   - Admin tier: Full access to `maintenance_jobs`, `page_owners`
7. Create indexes for performance

**Files**:
- Database migration script
- Permission grant script

### Phase 2: User Page System

**Tasks**:
1. Create `User` page class (derived from `Page`)
2. Create `Person` and `Company` page classes (derived from `User`)
3. Register page classes with `@register_page_class`
4. Implement user page creation logic
5. Test user page CRUD operations

**Files**:
- `hh/page/user.py` (User page class)
- `hh/page/person.py` (Person page class)
- `hh/page/company.py` (Company page class)

### Phase 3: Authentication System

**Tasks**:
1. Implement magic link token generation and validation
2. Implement OAuth integration (Google, GitHub, Apple, X)
3. Implement token storage in `user_auth_tokens` table
4. Implement user matching logic (email, OAuth ID)
5. Create authentication routes (`/request-magic-link`, `/verify`, `/oauth/callback`)
6. Test authentication flows

**Files**:
- `hh/auth/magic_link.py` (magic link functions)
- `hh/auth/oauth.py` (OAuth integration)
- `hh/auth/token_manager.py` (token storage/retrieval)
- `hh/deploy/flask/routes/auth.py` (authentication routes)

### Phase 4: Session System

**Tasks**:
1. Implement session creation after authentication
2. Implement session lookup middleware
3. Implement session refresh logic
4. Implement session cleanup (cron job)
5. Integrate session tier with Gateway credential loading
6. Test session persistence and expiration

**Files**:
- `hh/auth/session.py` (session management)
- Modify `hh/deploy/flask/app.py` (add session middleware)
- Modify `hh/deploy/flask/http_client.py` (pass tier to Gateway)

### Phase 5: Ownership System

**Tasks**:
1. Implement ownership check functions
2. Implement ownership inheritance logic
3. Implement automatic ownership on page creation
4. Create admin panel for ownership assignment
5. Test ownership checks and inheritance

**Files**:
- `hh/page/ownership.py` (ownership check functions)
- Modify `hh/page/page.py` (automatic ownership on creation)
- `hh/deploy/flask/routes/admin/ownership.py` (admin panel routes)

### Phase 6: Maintenance Queue Integration

**Tasks**:
1. Enhance maintenance job enqueueing to include `requested_by_page_id` and `target_page_id`
2. Implement whitelist checking (scan `@register_maintenance_tool` decorators)
3. Enhance maintenance daemon to check ownership before executing
4. Implement `pending_review` status handling
5. Create initial whitelisted job types (`edit_page_text`, `upload_image`, etc.)
6. Test job enqueueing and processing

**Files**:
- Modify `hh/deploy/maint/job_queue.py` (enhance job enqueueing)
- Modify `hh/deploy/maint/worker.py` (add ownership checks)
- Create initial maintenance tools for verified users
- `hh/gateway/registry/maintenance_whitelist.py` (whitelist checking)

### Phase 7: MCP Integration

**Tasks**:
1. Create MCP tools for job enqueueing (`enqueue_maintenance_job`)
2. Create MCP tool for job status checking (`get_maintenance_job_status`)
3. Integrate with TypeScript `RPCClient`
4. Test MCP job enqueueing and status polling

**Files**:
- `hh/page/enqueue_job.py` (MCP tool for enqueueing)
- `hh/page/job_status.py` (MCP tool for status)
- Modify TypeScript `RPCClient` (add job methods)

### Phase 8: Admin Panel

**Tasks**:
1. Create admin panel for ownership assignment
2. Create admin panel for job review (`pending_review` jobs)
3. Create admin panel for user management
4. Test admin panel functionality

**Files**:
- `hh/deploy/flask/routes/admin/ownership.py` (ownership management)
- `hh/deploy/flask/routes/admin/jobs.py` (job review)
- `hh/deploy/flask/routes/admin/users.py` (user management)
- Admin panel templates

### Phase 9: Testing & Security

**Tasks**:
1. Test authentication flows (magic links, OAuth)
2. Test session management and expiration
3. Test ownership checks and inheritance
4. Test maintenance queue processing
5. Test permission system (database + business logic)
6. Security audit (token strength, SQL injection, CSRF, etc.)
7. Performance testing (session lookup, ownership checks)

---

## 11. Integration Points

### With Flask App

**Current State**:
- Tier determined by instance configuration
- No session management
- Static tier per instance

**After Implementation**:
- Tier determined by session (default to 1 if no session)
- Session middleware loads tier from database
- Dynamic tier elevation possible
- `user_page_id` available in request context

**Changes Needed**:
- Add session middleware to `app.py`
- Modify tier detection logic
- Add auth routes
- Pass `user_page_id` to request handlers

### With Gateway System

**Current State**:
- Gateway uses default credentials
- No tier context passed

**After Implementation**:
- Flask determines tier from session
- Pass tier to Gateway subprocess
- Gateway loads tier-specific credentials from `~/.henhouse_{tier}/.project.cnf`
- `user_page_id` passed to Gateway for ownership checks

**Changes Needed**:
- Modify `http_client.py` to accept tier and `user_page_id` parameters
- Modify Gateway credential loading
- Test tier-specific database access

### With Page System

**Current State**:
- Page CRUD operations available to admin/root only
- No ownership system

**After Implementation**:
- User pages inherit all Page functionality
- Ownership checks before modifications
- Automatic ownership on page creation
- Ownership inheritance from parent pages

**Changes Needed**:
- Create User/Person/Company page classes
- Add ownership check functions
- Modify page creation to set ownership
- Integrate ownership checks into CRUD operations

### With Maintenance System

**Current State**:
- Maintenance daemon processes admin-initiated jobs only
- No user-initiated jobs

**After Implementation**:
- Verified users can enqueue jobs
- Daemon checks ownership before executing
- Jobs can be `pending_review` for manual/agent review
- Whitelist system prevents arbitrary command execution

**Changes Needed**:
- Enhance `maintenance_jobs` table
- Add ownership checks to daemon
- Implement whitelist checking
- Create initial whitelisted job types

### With MCP System

**Current State**:
- MCP tools available to all tiers (based on whitelist)
- No user context in MCP requests

**After Implementation**:
- MCP requests include `user_page_id` from session
- Job enqueueing MCP tools for verified users
- Job status checking MCP tools
- Ownership-aware MCP tools

**Changes Needed**:
- Modify MCP request handling to include `user_page_id`
- Create job enqueueing MCP tools
- Create job status MCP tools
- Update MCP whitelist for verified tier

### With TypeScript Client

**Current State**:
- No user authentication UI
- No job status UI

**After Implementation**:
- Authentication UI (magic link request, OAuth buttons)
- Job enqueueing via MCP (transparent to user)
- Job status polling UI
- User profile pages

**Changes Needed**:
- Create authentication UI components
- Integrate job enqueueing into existing CRUD operations
- Create job status polling component
- Create user profile page components

---

## Security Considerations

### Token Security
- Use `secrets.token_urlsafe(64)` for token generation
- Tokens must be cryptographically secure (not sequential, not guessable)
- Magic link tokens: One-time use, expiration enforced
- OAuth tokens: Stored securely, encrypted if possible

### Rate Limiting
- Limit magic link requests per email (e.g., 3 per hour)
- Limit magic link requests per IP (e.g., 10 per hour)
- Limit job enqueueing per user (e.g., 100 per hour)
- Prevent email enumeration attacks

### Session Security
- Session IDs must be cryptographically secure
- Use HTTPS for cookie transmission
- Set secure cookie flags (HttpOnly, Secure, SameSite)
- Implement session fixation protection
- Sliding expiration on activity

### Database Security
- Use parameterized queries (prevent SQL injection)
- Minimal permissions (table-level grants only)
- Regular cleanup of expired tokens/sessions
- Ownership checks prevent unauthorized modifications

### OAuth Security
- Validate OAuth callbacks (state parameter)
- Store OAuth tokens securely (encrypted)
- Handle OAuth token refresh
- Prevent OAuth token reuse attacks

### Ownership Security
- Ownership checks before every modification
- Inheritance checks prevent privilege escalation
- Admin override for ownership assignment (manual only)
- Audit trail via `created_by_page_id` in `page_owners`

### Job Queue Security
- Whitelist prevents arbitrary command execution
- Ownership checks before job execution
- `pending_review` status for unauthorized requests
- Job status visible only to requester (or admin)

---

## Testing Checklist

### Authentication Flow
- [ ] Request magic link with valid email
- [ ] Request magic link with invalid email format
- [ ] Rate limiting works (too many requests)
- [ ] Email is sent successfully
- [ ] Token validation works (valid token)
- [ ] Token validation fails (invalid token)
- [ ] Token validation fails (expired token)
- [ ] Token validation fails (already used)
- [ ] OAuth flow works (Google, GitHub, Apple, X)
- [ ] OAuth callback validation works
- [ ] User page created/retrieved correctly
- [ ] Session created after authentication

### Session Management
- [ ] Session persists across requests
- [ ] Session tier is correct (tier 2)
- [ ] Session expiration works
- [ ] Session cleanup removes expired sessions
- [ ] Invalid session_id handled gracefully
- [ ] Missing session defaults to tier 1
- [ ] Session refresh updates last_activity

### User Pages
- [ ] User page creation works
- [ ] User page inherits Page functionality
- [ ] Person and Company page classes work
- [ ] User metadata stored correctly
- [ ] Auth tokens stored separately (not in metadata)

### Ownership System
- [ ] Ownership check works (explicit ownership)
- [ ] Ownership inheritance works (parent ownership)
- [ ] Automatic ownership on page creation
- [ ] Multiple owners allowed
- [ ] Ownership assignment via admin panel
- [ ] Ownership revocation works

### Maintenance Queue
- [ ] Job enqueueing works (verified user)
- [ ] Whitelist checking works
- [ ] Ownership check before execution
- [ ] `pending_review` status for unauthorized requests
- [ ] Job status checking works
- [ ] Job processing by daemon works
- [ ] Error handling works

### Permission System
- [ ] Database permissions enforced (MySQL grants)
- [ ] Business logic permissions enforced (ownership checks)
- [ ] Whitelist prevents arbitrary commands
- [ ] Verified tier can enqueue jobs
- [ ] Verified tier cannot directly modify database
- [ ] Admin tier can process queue
- [ ] Admin tier can assign ownership

### Security
- [ ] Tokens are cryptographically secure
- [ ] Rate limiting prevents abuse
- [ ] SQL injection prevented
- [ ] Session fixation prevented
- [ ] Cookie security flags set
- [ ] OAuth callback validation works
- [ ] Ownership checks prevent unauthorized access

---

## Future Enhancements

### Potential Additions
- Password reset via magic links (if passwords are added)
- Email change verification
- Two-factor authentication
- Session management UI (view active sessions, revoke)
- Remember me functionality (longer session expiration)
- Agent curator loop for `pending_review` jobs
- Trust score system for users
- User activity tracking
- Ownership conflict resolution UI

### Performance Optimizations
- Session caching (Redis/Memcached)
- Ownership check caching
- Database connection pooling
- Index optimization
- Query optimization
- Job queue batching

### Puzzle Database Specific
- Designer/Manufacturer/Collector/Retailer relational tables
- Guild membership verification
- Artisan portfolio pages
- Production run tracking
- Collection tracking
- Sale tracking

---

This document provides a comprehensive roadmap for implementing the Tier 2 verification system. The implementation follows the existing Henhouse architecture patterns (page-derived classes, decorator-based registration, maintenance queue) and integrates cleanly with the Gateway, Page, and Maintenance systems.
