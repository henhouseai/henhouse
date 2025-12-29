# Chapter 3: SSL Certificates

## Quick Reference

Henhouse requires SSL certificates for secure database connections and HTTPS web access. This quick reference lists what you need to track and where it's used.

### Information to Track

| Component | What You Need | Where It's Used |
|-----------|---------------|-----------------|
| **Main Domain Certificate** | Let's Encrypt cert for `example.com` | NGINX HTTPS configuration |
| **Database Certificate** | Let's Encrypt cert for `db.example.com` | MySQL SSL, install config `ssl_ca_path` |
| **Cache Certificate** | Let's Encrypt cert for `cache.example.com` | MySQL SSL, install config `cache_ssl_ca_path` |
| **Webroot Path** | `/var/www/html` | Let's Encrypt ACME challenges |
| **MySQL SSL Directory** | `/etc/mysql/ssl/` | MySQL SSL certificate storage |
| **MySQL CA Path** | `/etc/mysql/ssl/ca.pem` | Install config: `ssl_ca_path`, `cache_ssl_ca_path` |
| **Let's Encrypt Live** | `/etc/letsencrypt/live/{domain}/` | Source certificates |
| **Renewal Hook** | `/etc/letsencrypt/renewal-hooks/deploy/` | Automatic certificate updates |

### Expected File Paths

**Let's Encrypt Certificates:**
- `/etc/letsencrypt/live/{domain}/` - Live certificates for each domain
  - `fullchain.pem` - Certificate chain (leaf + intermediate)
  - `privkey.pem` - Private key
  - `cert.pem` - Certificate only
  - `chain.pem` - Intermediate certificate

**MySQL SSL Directory:**
- `/etc/mysql/ssl/` - MySQL SSL certificate directory
- `/etc/mysql/ssl/ca.pem` - CA bundle (root + intermediate, no leaf)
- `/etc/mysql/ssl/server-cert.pem` - Server certificate (fullchain)
- `/etc/mysql/ssl/server-key.pem` - Server private key

**NGINX Configuration:**
- NGINX uses Let's Encrypt certificates directly from `/etc/letsencrypt/live/{domain}/`
- No copying needed for web certificates

## SSL Certificate Architecture

### Certificate Types

Henhouse uses two types of SSL certificates:

1. **Web Certificates**: For main domain, www, admin, and panel subdomains
   - Used by NGINX for HTTPS
   - Stored in `/etc/letsencrypt/live/{domain}/`
   - Accessed directly by NGINX (no copying needed)

2. **Database Certificates**: For `db.{domain}` and `cache.{domain}` subdomains
   - Used by MySQL for SSL connections
   - Stored in `/etc/letsencrypt/live/db.{domain}/`
   - **Copied** to `/etc/mysql/ssl/` (MySQL cannot use symlinks)

### Why Separate Database Certificates?

Database subdomains use separate certificates because:
- Database connections require SSL certificates
- Certificates must be accessible to MySQL process
- Renewal must update MySQL configuration automatically
- MySQL cannot use symlinks to Let's Encrypt certificates (permission issues)

## Let's Encrypt Setup

### Prerequisites

Before obtaining SSL certificates:
1. **NGINX must be installed** (see Chapter 1)
2. **DNS must be configured** (see Chapter 1)
3. **HTTP deployment must be completed** (see `http-nginx.md` for HTTP-only setup)
4. **Webroot directory exists**: `/var/www/html`

### Webroot Mode

Henhouse uses **webroot mode** for all Let's Encrypt certificates:
- **Webroot Path**: `/var/www/html` (standardized across all certificates)
- **Challenge Location**: `/.well-known/acme-challenge/`
- **No Service Disruption**: NGINX remains running during certificate operations

**Why Webroot Mode?**
- No need to stop/start NGINX (avoids service disruption)
- Works seamlessly with existing NGINX configurations
- Allows automatic renewal without manual intervention
- Compatible with all domain types (main, admin, panel, db, cache)

### HTTP Redirect Block with ACME Exception

Your NGINX HTTP configuration must include an exception for Let's Encrypt ACME challenges:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com admin.example.com panel.example.com db.example.com cache.example.com;

    # Allow Let's Encrypt ACME challenges (must be on HTTP for webroot validation)
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    # Redirect all other HTTP traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}
```

This configuration:
- Serves ACME challenge files from `/var/www/html/.well-known/acme-challenge/` on HTTP (port 80)
- Redirects all other HTTP traffic to HTTPS
- Automatically includes `db.{domain}` and `cache.{domain}` subdomains

## Obtaining Certificates

### Main Domain Certificate

For your main domain and web subdomains:

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d example.com \
  -d www.example.com \
  -d admin.example.com \
  -d panel.example.com
```

### Database Certificate

For database subdomains (required for MySQL SSL):

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d db.example.com \
  -d cache.example.com
```

**Important**: NGINX must serve `/.well-known/acme-challenge/` from `/var/www/html` for these domains.

## MySQL SSL Setup

### 1. Create MySQL SSL Directory

```bash
sudo mkdir -p /etc/mysql/ssl
```

### 2. Copy Certificates

Copy certificates from Let's Encrypt to MySQL SSL directory:

```bash
# What MySQL serves: leaf + intermediate
sudo cp -L /etc/letsencrypt/live/db.example.com/fullchain.pem /etc/mysql/ssl/server-cert.pem

# What clients trust: root + intermediate (no leaf)
sudo sh -c 'cat /etc/ssl/certs/ISRG_Root_X1.pem /etc/letsencrypt/live/db.example.com/chain.pem > /etc/mysql/ssl/ca.pem'

# Private key
sudo cp -L /etc/letsencrypt/live/db.example.com/privkey.pem /etc/mysql/ssl/server-key.pem
```

**Notes**:
- `-L` dereferences symlinks (copies real files)
- `server-cert.pem` must be `fullchain.pem` so MySQL presents the intermediate
- `ca.pem` must be **root + intermediate only** (no leaf)

### 3. Set Ownership and Permissions

```bash
sudo chown mysql:mysql /etc/mysql/ssl/*
sudo chmod 644 /etc/mysql/ssl/ca.pem
sudo chmod 644 /etc/mysql/ssl/server-cert.pem
sudo chmod 600 /etc/mysql/ssl/server-key.pem
```

**Permissions**:
- `644`: Readable by all, writable by owner (certificates)
- `600`: Readable/writable by owner only (private key)
- `mysql:mysql`: Owned by MySQL user/group

### 4. Configure MySQL

Add SSL configuration to MySQL config file (`/etc/mysql/mysql.conf.d/mysqld.cnf`):

```ini
[mysqld]
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem
```

**Important**: Use **absolute paths** (not relative paths). MySQL must be able to find the certificate files using the full path.

### 5. Restart MySQL

```bash
sudo systemctl restart mysql
```

## Automatic Certificate Renewal

### Renewal Hook Script

Create a renewal hook to automatically update MySQL certificates when Let's Encrypt certificates are renewed:

```bash
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy
```

Create `/etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh`:

```bash
#!/bin/bash
set -euo pipefail

SSL_DIR=/etc/mysql/ssl
LE_LIVE=/etc/letsencrypt/live/db.example.com
ROOT_CA=/etc/ssl/certs/ISRG_Root_X1.pem

cp -L "$LE_LIVE/fullchain.pem" "$SSL_DIR/server-cert.pem"   # leaf + intermediate
cat "$ROOT_CA" "$LE_LIVE/chain.pem" > "$SSL_DIR/ca.pem"     # root + intermediate
cp -L "$LE_LIVE/privkey.pem" "$SSL_DIR/server-key.pem"

chown mysql:mysql "$SSL_DIR"/server-cert.pem "$SSL_DIR"/server-key.pem "$SSL_DIR"/ca.pem
chmod 644 "$SSL_DIR"/server-cert.pem "$SSL_DIR"/ca.pem
chmod 600 "$SSL_DIR"/server-key.pem

systemctl restart mysql
```

Make it executable:

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh
```

This hook runs automatically when Certbot renews certificates.

## Technical Details: Certificate Renewal Configuration

Renewal configs are stored in `/etc/letsencrypt/renewal/{domain}.conf`:

```ini
authenticator = webroot
server = https://acme-v02.api.letsencrypt.org/directory
key_type = ecdsa
webroot_path = /var/www/html,
[[webroot_map]]
example.com = /var/www/html
www.example.com = /var/www/html
admin.example.com = /var/www/html
panel.example.com = /var/www/html
```

**Key Settings**:
- `authenticator = webroot`: Uses webroot mode
- `webroot_path = /var/www/html,`: Standardized webroot path
- `[[webroot_map]]`: Per-domain webroot paths (all use `/var/www/html`)

Certbot automatically renews certificates via systemd timer:
- Checks for expiring certificates twice daily
- Renews certificates that expire within 30 days
- Runs renewal hooks (pre, deploy, post) automatically

**Manual Renewal Testing**:
```bash
sudo certbot renew --dry-run
```

This tests the renewal process without actually renewing certificates.

## Technical Details: Renewal Hooks

Certbot supports renewal hooks in `/etc/letsencrypt/renewal-hooks/`:
- **pre/**: Scripts run before renewal
- **deploy/**: Scripts run after successful renewal
- **post/**: Scripts run after renewal (success or failure)

The MySQL SSL deploy hook (see MySQL SSL setup section) copies certificates, sets permissions, and restarts MySQL automatically when certificates are renewed.

## Install Config Values

The following SSL-related values go into `/root/.{project}-install.cnf`:

```ini
[install]
# SSL CA paths (absolute paths)
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem
```

**Note**: Both `ssl_ca_path` and `cache_ssl_ca_path` typically point to the same file (`/etc/mysql/ssl/ca.pem`) since both database subdomains use the same certificate.

## Verification

Before proceeding to installation, verify:

1. **Certificates exist**:
   ```bash
   ls -la /etc/letsencrypt/live/db.example.com/
   ```

2. **MySQL SSL files exist**:
   ```bash
   ls -la /etc/mysql/ssl/
   ```

3. **MySQL SSL is configured**:
   ```bash
   grep -E "ssl-ca|ssl-cert|ssl-key" /etc/mysql/mysql.conf.d/mysqld.cnf
   ```

4. **MySQL can read SSL files**:
   ```bash
   sudo -u mysql ls -la /etc/mysql/ssl/
   ```

## Troubleshooting

### MySQL Cannot Read SSL Files

**Problem**: MySQL fails to start or SSL connections fail

**Solutions**:
1. Verify file ownership: `ls -la /etc/mysql/ssl/` (should be `mysql:mysql`)
2. Check file permissions: Private key should be `600`, certificates should be `644`
3. Ensure files are actual files (not symlinks): `file /etc/mysql/ssl/*`
4. Verify MySQL config points to correct paths

### Certificate Renewal Doesn't Update MySQL

**Problem**: Certificates renew but MySQL still uses old certificates

**Solutions**:
1. Verify renewal hook is executable: `ls -la /etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh`
2. Check hook runs during renewal: Review Certbot logs
3. Test hook manually: Run script directly to verify it works
4. Check MySQL service restarts: Verify `systemctl restart mysql` succeeds

### Permission Denied Errors

**Problem**: Cannot copy certificates or set permissions

**Solutions**:
1. Ensure running with sudo/root privileges
2. Verify `/etc/mysql/ssl/` directory exists and is writable
3. Check Let's Encrypt certificate files are readable
4. Verify MySQL user/group exists: `id mysql`

### SSL Verification Fails (Unable to Get Local Issuer)

**Problem**: Clients fail SSL verification with "unable to get local issuer certificate"

**Solutions**:
1. Ensure MySQL serves `fullchain.pem` as `server-cert.pem` (so the intermediate is sent)
2. Ensure `ca.pem` contains **root + intermediate only** (no leaf certificate)
3. Ensure client config uses `ssl_verify_mode=2` and `ssl_ca` points to the readable `ca.pem` file

## Next Steps

Once SSL certificates are configured:
1. Proceed to **Chapter 5: Installation** to run the installer
2. The installer will use the SSL CA paths you configured

