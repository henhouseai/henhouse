# Tier 2 Verification System

This document covers the planned implementation of the Tier 2 (verified) authentication system using magic links and database-backed sessions. This system allows guest users (Tier 1) to elevate to verified status (Tier 2) through email-based verification.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Database Schema](#2-database-schema)
3. [Authentication Flow](#3-authentication-flow)
4. [Session Management](#4-session-management)
5. [Implementation Plan](#5-implementation-plan)
6. [Integration Points](#6-integration-points)

## Agent Quick Reference

- **Purpose**: Allow Tier 1 (guest) users to elevate to Tier 2 (verified) via email magic links
- **Database Tables**: `magic_links` (tokens), `sessions` (session data)
- **Session Storage**: Database-backed (Flask-Session or custom), cookie stores session_id only
- **Flow**: Request link → Email sent → Click link → Validate → Create session → Elevate tier
- **Permissions**: Guest tier needs INSERT on `magic_links`, INSERT on `sessions`; Verified tier needs SELECT/UPDATE on `sessions`

## Agent Training Notes

### Tier System Context
- **Tier 1 (Guest)**: Default, read-only, no authentication required
- **Tier 2 (Verified)**: Elevated via magic link, moderate DB writes
- **Tier 3 (Admin)**: HTTP Basic Auth on `admin.{domain}` subdomain
- **Tier 4 (Root)**: HTTP Basic Auth on `panel.{domain}` subdomain

### Current State
- Tier 1, 3, 4 are working (static tier per Flask instance)
- Tier 2 does not exist yet (orphaned user/DB account)
- No session management currently implemented
- Tier determined by Flask script name (`app_guest.py` → guest)

### Design Principles
- **Standard Patterns**: Use Flask-Session or standard Flask session patterns
- **Database-Driven**: Session data in database, cookie only stores session_id
- **Minimal Permissions**: Table-level grants, bare minimum needed
- **Security**: Cryptographically secure tokens, expiration, one-time use

---

## 1. System Overview

The Tier 2 verification system enables dynamic tier elevation from guest (Tier 1) to verified (Tier 2) status. Unlike Tiers 3 and 4 which use static subdomain-based authentication, Tier 2 requires session-based authentication that can be initiated from the main guest site.

### Architecture

```
Guest User (Tier 1)
    ↓
Requests Magic Link (provides email)
    ↓
Token Generated → Stored in DB → Email Sent
    ↓
User Clicks Link → Token Validated
    ↓
Session Created in DB → Cookie Set → Tier Elevated to 2
    ↓
Subsequent Requests: Cookie → DB Lookup → Tier 2 Access
```

### Key Components

- **Magic Link System**: Token generation, email sending, validation
- **Session System**: Database-backed sessions with cookie-based session_id
- **Tier Elevation**: Dynamic tier switching via session (unlike static Tiers 3/4)
- **Gateway Integration**: Session tier passed to Gateway for credential loading

---

## 2. Database Schema

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

**Fields:**
- `token`: Cryptographically secure random token (64 chars)
- `email`: User's email address
- `expires_at`: Token expiration (typically 15 minutes)
- `used`: Boolean flag to prevent reuse
- `created_at`: Timestamp for audit

**Permissions:**
- Guest tier: INSERT, SELECT, UPDATE (for validation)
- Other tiers: No access needed

### sessions Table

Stores active user sessions with tier information.

```sql
CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    tier INT NOT NULL,
    email VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_expires (expires_at),
    INDEX idx_email (email)
);
```

**Fields:**
- `session_id`: Unique session identifier (stored in cookie)
- `tier`: User's tier level (2 for verified)
- `email`: User's email address
- `created_at`: Session creation timestamp
- `expires_at`: Session expiration (typically 30 days)
- `last_activity`: Last request timestamp (for cleanup)

**Permissions:**
- Guest tier: INSERT (creates session after validation)
- Verified tier: SELECT, UPDATE (refresh own session)
- Other tiers: No access needed

---

## 3. Authentication Flow

### Step 1: Magic Link Request

**Route**: `POST /request-magic-link`

**Process:**
1. User provides email address
2. Validate email format
3. Generate cryptographically secure token (64 chars)
4. Calculate expiration (15 minutes from now)
5. INSERT into `magic_links` table
6. Send email with verification link
7. Return success response

**Email Content:**
- Subject: "Verify your email for [Site Name]"
- Body: Link to `/verify?token={token}`
- Expiration notice: "Link expires in 15 minutes"

**Error Handling:**
- Invalid email format → 400 Bad Request
- Rate limiting (prevent abuse) → 429 Too Many Requests
- Email send failure → Log error, return generic success (security)

### Step 2: Magic Link Validation

**Route**: `GET /verify?token={token}`

**Process:**
1. Extract token from URL parameter
2. SELECT from `magic_links` WHERE token = ? AND used = FALSE
3. Validate token exists and not expired
4. If valid:
   - UPDATE `magic_links` SET used = TRUE
   - Generate `session_id` (cryptographically secure)
   - Calculate session expiration (30 days from now)
   - INSERT into `sessions` table (tier=2, email, expires_at)
   - Flask sets cookie with `session_id`
   - Redirect to verified content area
5. If invalid/expired:
   - Show error page
   - Option to request new link

**Security:**
- One-time use enforced (used flag)
- Expiration enforced (expires_at check)
- Token must be cryptographically secure (not guessable)

### Step 3: Session Usage

**On Every Request:**
1. Flask reads `session_id` from cookie
2. SELECT from `sessions` WHERE session_id = ? AND expires_at > NOW()
3. If found:
   - Get tier from session record
   - Update `last_activity` timestamp
   - Use tier for Gateway credential loading
4. If not found/expired:
   - Clear cookie
   - Default to tier 1 (guest)

**Session Refresh:**
- Update `last_activity` on each request
- Optionally extend `expires_at` on activity (sliding expiration)
- Cleanup expired sessions via cron job

---

## 4. Session Management

### Flask Session Configuration

**Option A: Flask-Session Extension**
```python
from flask_session import Session

app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
Session(app)
```

**Option B: Custom Database Session**
```python
from flask import session

# Custom session middleware
@app.before_request
def load_session():
    session_id = request.cookies.get('session_id')
    if session_id:
        # Lookup in database
        session_data = get_session_from_db(session_id)
        if session_data:
            session['tier'] = session_data['tier']
            session['email'] = session_data['email']
            update_session_activity(session_id)
        else:
            # Expired/invalid, clear cookie
            session.clear()
    else:
        # No session, default to tier 1
        session['tier'] = 1
```

### Session Helper Functions

```python
def get_session_tier():
    """Get current user's tier from session."""
    return session.get('tier', 1)

def set_session_tier(tier, email):
    """Create new session with tier and email."""
    session_id = generate_session_id()
    expires_at = datetime.now() + timedelta(days=30)
    create_session_in_db(session_id, tier, email, expires_at)
    response.set_cookie('session_id', session_id, max_age=30*24*60*60)
    session['tier'] = tier
    session['email'] = email

def clear_session():
    """Invalidate current session."""
    session_id = request.cookies.get('session_id')
    if session_id:
        delete_session_from_db(session_id)
    session.clear()
    response.set_cookie('session_id', '', expires=0)
```

### Session Cleanup

**Cron Job** (runs daily):
```sql
-- Delete expired sessions
DELETE FROM sessions WHERE expires_at < NOW();

-- Delete expired magic links
DELETE FROM magic_links WHERE expires_at < NOW() OR (used = TRUE AND created_at < DATE_SUB(NOW(), INTERVAL 1 DAY));
```

---

## 5. Implementation Plan

### Phase 1: Database Setup

**Tasks:**
1. Create `magic_links` table
2. Create `sessions` table
3. Grant permissions:
   - Guest tier: INSERT on `magic_links`, SELECT/UPDATE on `magic_links`, INSERT on `sessions`
   - Verified tier: SELECT/UPDATE on `sessions`
4. Create indexes for performance

**Files:**
- Database migration script
- Permission grant script

**Estimated Time**: 1-2 hours

### Phase 2: Token System

**Tasks:**
1. Create token generation function (cryptographically secure)
2. Create token validation function
3. Create token cleanup function
4. Add rate limiting for magic link requests

**Files:**
- `hh/auth/magic_link.py` (token functions)
- `hh/auth/rate_limit.py` (rate limiting)

**Estimated Time**: 2-3 hours

### Phase 3: Email System

**Tasks:**
1. Configure SMTP settings (or email service)
2. Create email template (HTML/text)
3. Create email sending function
4. Error handling for email failures
5. Testing with real email addresses

**Files:**
- `hh/auth/email.py` (email sending)
- `hh/auth/templates/` (email templates)
- Configuration file for SMTP settings

**Estimated Time**: 3-4 hours

### Phase 4: Flask Session Setup

**Tasks:**
1. Install Flask-Session or implement custom session middleware
2. Configure session storage (database)
3. Create session helper functions
4. Add session loading to request pipeline
5. Test session creation and retrieval

**Files:**
- `hh/auth/session.py` (session management)
- Modify `hh/deploy/flask/app.py` (add session middleware)

**Estimated Time**: 2-3 hours

### Phase 5: Magic Link Routes

**Tasks:**
1. Create `/request-magic-link` route (POST)
2. Create `/verify?token=...` route (GET)
3. Create error pages (invalid token, expired token)
4. Add redirect logic after verification
5. Test full flow end-to-end

**Files:**
- `hh/deploy/flask/routes/auth.py` (new file)
- Modify `hh/deploy/flask/app.py` (register routes)
- `hh/deploy/site/templates/auth/` (error pages)

**Estimated Time**: 2-3 hours

### Phase 6: Gateway Integration

**Tasks:**
1. Modify `http_client.py` to read session tier
2. Pass tier to Gateway subprocess calls
3. Modify Gateway credential loading to use tier-specific config
4. Test tier-based credential loading
5. Verify verified tier can perform DB writes

**Files:**
- Modify `hh/deploy/flask/http_client.py`
- Modify Gateway credential loading (likely in connection module)
- Test with verified tier operations

**Estimated Time**: 3-4 hours

### Phase 7: Testing & Security

**Tasks:**
1. Test magic link generation and validation
2. Test session creation and persistence
3. Test tier elevation and Gateway integration
4. Test expiration handling
5. Test rate limiting
6. Security audit (token strength, SQL injection, etc.)
7. Performance testing (session lookup overhead)

**Estimated Time**: 2-3 hours

**Total Estimated Time**: 15-22 hours

---

## 6. Integration Points

### With Flask App

**Current State:**
- Tier determined by script name (`app_guest.py` → guest)
- No session management
- Static tier per instance

**After Implementation:**
- Tier determined by session (default to 1 if no session)
- Session middleware loads tier from database
- Dynamic tier elevation possible

**Changes Needed:**
- Add session middleware to `app.py`
- Modify tier detection logic
- Add auth routes

### With Gateway System

**Current State:**
- Gateway uses default credentials
- No tier context passed

**After Implementation:**
- Flask determines tier from session
- Pass tier to Gateway subprocess
- Gateway loads tier-specific credentials from `~/.henhouse_{tier}/.project.cnf`

**Changes Needed:**
- Modify `http_client.py` to accept tier parameter
- Modify Gateway credential loading
- Test tier-specific database access

### With Database Connection

**Current State:**
- Database connection uses default credentials
- No tier-based credential loading

**After Implementation:**
- Load credentials based on session tier
- Guest tier: `~/.henhouse_guest/.project.cnf`
- Verified tier: `~/.henhouse_verified/.project.cnf`
- Admin tier: `~/.henhouse_admin/.project.cnf`
- Root tier: `~/.henhouse_root/.project.cnf`

**Changes Needed:**
- Modify credential loading function
- Ensure tier-specific config files exist
- Test each tier's database permissions

### With Existing Authentication

**Tier 1 (Guest)**: No changes needed
- Still default, no authentication
- Can now request magic link

**Tier 3 (Admin)**: No changes needed
- Still uses HTTP Basic Auth on `admin.{domain}`
- Static tier per instance

**Tier 4 (Root)**: No changes needed
- Still uses HTTP Basic Auth on `panel.{domain}`
- Static tier per instance

**Tier 2 (Verified)**: New system
- Only way to access is via magic link from Tier 1
- Session-based, dynamic tier elevation

---

## Security Considerations

### Token Security
- Use `secrets.token_urlsafe(64)` for token generation
- Tokens must be cryptographically secure (not sequential, not guessable)
- Store tokens as-is (no hashing needed, one-time use)

### Rate Limiting
- Limit magic link requests per email (e.g., 3 per hour)
- Limit magic link requests per IP (e.g., 10 per hour)
- Prevent email enumeration attacks

### Session Security
- Session IDs must be cryptographically secure
- Use HTTPS for cookie transmission
- Set secure cookie flags (HttpOnly, Secure, SameSite)
- Implement session fixation protection

### Database Security
- Use parameterized queries (prevent SQL injection)
- Minimal permissions (table-level grants only)
- Regular cleanup of expired tokens/sessions

### Email Security
- Don't reveal if email exists in system (prevent enumeration)
- Generic error messages for failures
- Log email send failures for monitoring

---

## Testing Checklist

### Magic Link Flow
- [ ] Request magic link with valid email
- [ ] Request magic link with invalid email format
- [ ] Rate limiting works (too many requests)
- [ ] Email is sent successfully
- [ ] Token validation works (valid token)
- [ ] Token validation fails (invalid token)
- [ ] Token validation fails (expired token)
- [ ] Token validation fails (already used)
- [ ] Session created after validation
- [ ] Cookie set correctly

### Session Management
- [ ] Session persists across requests
- [ ] Session tier is correct (tier 2)
- [ ] Session expiration works
- [ ] Session cleanup removes expired sessions
- [ ] Invalid session_id handled gracefully
- [ ] Missing session defaults to tier 1

### Gateway Integration
- [ ] Tier 2 credentials loaded correctly
- [ ] Tier 2 can perform DB writes
- [ ] Tier 2 cannot perform file writes (Unix permissions)
- [ ] Tier 2 operations work through Gateway
- [ ] Session tier passed correctly to Gateway

### Security
- [ ] Tokens are cryptographically secure
- [ ] Rate limiting prevents abuse
- [ ] SQL injection prevented
- [ ] Session fixation prevented
- [ ] Cookie security flags set

---

## Future Enhancements

### Potential Additions
- Password reset via magic links
- Email change verification
- Two-factor authentication
- Session management UI (view active sessions, revoke)
- Remember me functionality (longer session expiration)
- Email verification for account creation

### Performance Optimizations
- Session caching (Redis/Memcached)
- Database connection pooling
- Index optimization
- Query optimization

---

This document provides a comprehensive roadmap for implementing the Tier 2 verification system. The implementation follows standard Flask patterns and integrates cleanly with the existing Gateway architecture.

