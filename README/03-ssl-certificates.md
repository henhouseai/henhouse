# Chapter 3: SSL Certificates

## Quick Reference

Henhouse supports SSL/TLS certificates for secure database connections and HTTPS web access. **Note**: TLS/SSL is optional - for localhost deployments, plain text connections are supported (`mysql_tls_enabled = 0`, `ssl_enabled = 0`). This quick reference lists what you need to track and where it's used.

### Information to Track

| Component | Config Key | Default Value | Where It's Used |
|-----------|-----------|---------------|-----------------|
| **Main Domain Certificate** | (auto-detected) | Let's Encrypt or self-signed | NGINX HTTPS configuration |
| **Database Certificate** | (auto-detected) | Let's Encrypt or self-signed | MySQL SSL (only if `mysql_tls_enabled = 1`) |
| **Cache Certificate** | (auto-detected) | Let's Encrypt or self-signed | MySQL SSL (only if `mysql_tls_enabled = 1`) |
| **Webroot Path** | `webroot_dir` | `/var/www/html` | Let's Encrypt ACME challenges |
| **MySQL SSL Directory** | `mysql_ssl_dir` | `/etc/mysql/ssl` | MySQL SSL certificate storage |
| **MySQL Server Cert Path** | `mysql_server_cert_path` | `/etc/mysql/ssl/server-cert.pem` | MySQL server certificate |
| **MySQL Server Key Path** | `mysql_server_key_path` | `/etc/mysql/ssl/server-key.pem` | MySQL server private key |
| **MySQL CA Path** | `ssl_ca_path` | `/etc/mysql/ssl/ca.pem` | Install config (only if `mysql_tls_enabled = 1`) |
| **Cache CA Path** | `cache_ssl_ca_path` | `/etc/mysql/ssl/ca.pem` | Install config (only if `mysql_tls_enabled = 1`) |
| **Let's Encrypt Live** | (fixed path) | `/etc/letsencrypt/live/{domain}/` | Source certificates |
| **Renewal Hook** | (manual setup) | `/etc/letsencrypt/renewal-hooks/deploy/` | **Manual**: Certificate renewal updates (see below) |

### File Paths

**Hardcoded Paths (not configurable):**
- `/etc/letsencrypt/live/{domain}/` - Let's Encrypt certificate storage (fixed by certbot)
  - `fullchain.pem` - Certificate chain (leaf + intermediate)
  - `privkey.pem` - Private key
  - `cert.pem` - Certificate only
  - `chain.pem` - Intermediate certificate

**Configurable Paths (default values shown, can be changed in install config):**
- `webroot_dir` - Default: `/var/www/html` - Webroot for Let's Encrypt ACME challenges
- `mysql_ssl_dir` - Default: `/etc/mysql/ssl` - MySQL SSL certificate directory
- `mysql_server_cert_path` - Default: `/etc/mysql/ssl/server-cert.pem` - Server certificate (fullchain)
- `mysql_server_key_path` - Default: `/etc/mysql/ssl/server-key.pem` - Server private key
- `ssl_ca_path` - Default: `/etc/mysql/ssl/ca.pem` - CA bundle (root + intermediate, no leaf) - Only used if `mysql_tls_enabled = 1`
- `cache_ssl_ca_path` - Default: `/etc/mysql/ssl/ca.pem` - Cache CA path - Only used if `mysql_tls_enabled = 1`

**NGINX Configuration:**
- NGINX uses Let's Encrypt certificates directly from `/etc/letsencrypt/live/{domain}/`
- No copying needed for web certificates

## Quick Start: Automated Certificate Setup

The easiest way to set up SSL certificates is using the automated methods built into Henhouse:

### NGINX Certificates (Web)

**For self-signed certificates** (local/testing):
```bash
deploy -self-cert
```

**For Let's Encrypt certificates** (public deployments):
```bash
deploy -get-cert
```

The `deploy` command automatically:
- Generates or obtains certificates
- Creates NGINX SSL configuration
- Installs and enables the NGINX config
- Reloads NGINX

### MySQL Certificates (Database)

**Only needed if `mysql_tls_enabled = 1` in your install config.**

**For self-signed certificates** (local/testing):
```bash
init-db -root --confirm -self-cert
```

**For Let's Encrypt certificates** (public deployments):
```bash
init-db -root --confirm -get-cert
```

The `init-db` command automatically:
- Generates or obtains certificates
- Copies certificates to MySQL SSL directory
- Sets correct ownership and permissions
- Validates certificate setup

**Note**: The automated methods handle certificate creation, but **you must manually set up the renewal hook** for MySQL certificates (see "Automatic Certificate Renewal" section below).

## SSL Certificate Architecture

### Certificate Types

Henhouse uses two types of SSL certificates:

1. **Web Certificates**: For main domain, www, admin, and panel subdomains
   - Used by NGINX for HTTPS
   - Stored in `/etc/letsencrypt/live/{domain}/`
   - Accessed directly by NGINX (no copying needed)
   - **Automated**: Use `deploy -self-cert` or `deploy -get-cert`

2. **Database Certificates**: For `db.{domain}` and `cache.{domain}` subdomains
   - Used by MySQL for SSL connections (only if `mysql_tls_enabled = 1`)
   - Stored in `/etc/letsencrypt/live/db.{domain}/`
   - **Copied** to `mysql_ssl_dir` (default: `/etc/mysql/ssl/`) - MySQL cannot use symlinks
   - **Automated**: Use `init-db -self-cert` or `init-db -get-cert`

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
3. **Deployment must be completed** (see Chapter 8 for deployment setup)
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

### Automated Method (Recommended)

**For NGINX certificates:**
- Use `deploy -self-cert` for self-signed certificates (local/testing)
- Use `deploy -get-cert` for Let's Encrypt certificates (public deployments)

**For MySQL certificates** (only if `mysql_tls_enabled = 1`):
- Use `init-db -root --confirm -self-cert` for self-signed certificates
- Use `init-db -root --confirm -get-cert` for Let's Encrypt certificates

The automated methods handle:
- Certificate generation/obtainment
- Directory creation
- File copying (for MySQL)
- Ownership and permissions
- NGINX/MySQL configuration

### Advanced: Manual Certificate Setup

If you need custom certificate configuration or want to understand the process, you can obtain certificates manually:

**Main Domain Certificate** (for NGINX):

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d example.com \
  -d www.example.com \
  -d admin.example.com \
  -d panel.example.com
```

**Database Certificate** (for MySQL, only if `mysql_tls_enabled = 1`):

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d db.example.com \
  -d cache.example.com
```

**Important**: NGINX must serve `/.well-known/acme-challenge/` from `webroot_dir` (default: `/var/www/html`) for these domains. The automated `deploy` command sets this up automatically.

## MySQL SSL Setup

**Note**: MySQL SSL setup is only needed if `mysql_tls_enabled = 1` in your install config. For localhost deployments with `mysql_tls_enabled = 0`, skip this section.

### Automated Method (Recommended)

Use the automated certificate setup during database initialization:

**For self-signed certificates:**
```bash
init-db -root --confirm -self-cert
```

**For Let's Encrypt certificates:**
```bash
init-db -root --confirm -get-cert
```

The automated method handles:
1. Creating MySQL SSL directory (`mysql_ssl_dir` from config, default: `/etc/mysql/ssl`)
2. Generating or obtaining certificates
3. Copying certificates to MySQL SSL directory
4. Setting ownership (`mysql:mysql`) and permissions (`644` for certs, `600` for key)
5. Configuring MySQL config file (`mysql_config_path` from config)
6. Validating certificate setup

**Note**: The automated method does **not** create the renewal hook script. You must set that up manually (see "Automatic Certificate Renewal" section below).

### Advanced: Manual MySQL SSL Setup

If you need custom configuration or want to understand the process, you can set up MySQL SSL manually:

**1. Create MySQL SSL Directory**

```bash
sudo mkdir -p /etc/mysql/ssl
```

Or use your configured `mysql_ssl_dir` path.

**2. Copy Certificates**

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
- Use your configured paths (`mysql_server_cert_path`, `mysql_server_key_path`, `ssl_ca_path`) instead of hardcoded paths

**3. Set Ownership and Permissions**

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

**4. Configure MySQL**

Add SSL configuration to MySQL config file (`mysql_config_path` from config, default: `/etc/mysql/mysql.conf.d/mysqld.cnf`):

```ini
[mysqld]
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem
```

**Important**: Use **absolute paths** (not relative paths). MySQL must be able to find the certificate files using the full path. Use your configured paths from the install config.

**5. Restart MySQL**

```bash
sudo systemctl restart mysql
```

## Automatic Certificate Renewal

### NGINX Certificates (Automatic)

NGINX certificates renew automatically via Certbot's systemd timer. NGINX reads certificates directly from `/etc/letsencrypt/live/{domain}/`, so no additional configuration is needed. Certificates are renewed automatically when they expire within 30 days.

### MySQL Certificates (Manual Setup Required)

**Important**: The renewal hook for MySQL certificates is **not automated** by the installer. You must create it manually.

When Let's Encrypt renews certificates, MySQL certificates must be copied from Let's Encrypt to the MySQL SSL directory. This requires a renewal hook script that you create and maintain.

**Create the renewal hook directory:**

```bash
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy
```

**Create the renewal hook script** `/etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh`:

```bash
#!/bin/bash
set -euo pipefail

# Update these paths to match your install config values
SSL_DIR=/etc/mysql/ssl
LE_LIVE=/etc/letsencrypt/live/db.example.com
ROOT_CA=/etc/ssl/certs/ISRG_Root_X1.pem

# Copy certificates
cp -L "$LE_LIVE/fullchain.pem" "$SSL_DIR/server-cert.pem"   # leaf + intermediate
cat "$ROOT_CA" "$LE_LIVE/chain.pem" > "$SSL_DIR/ca.pem"     # root + intermediate
cp -L "$LE_LIVE/privkey.pem" "$SSL_DIR/server-key.pem"

# Set ownership and permissions
chown mysql:mysql "$SSL_DIR"/server-cert.pem "$SSL_DIR"/server-key.pem "$SSL_DIR"/ca.pem
chmod 644 "$SSL_DIR"/server-cert.pem "$SSL_DIR"/ca.pem
chmod 600 "$SSL_DIR"/server-key.pem

# Restart MySQL to use new certificates
systemctl restart mysql
```

**Make it executable:**

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh
```

**Important Notes:**
- Update the paths in the script (`SSL_DIR`, `LE_LIVE`) to match your install config values
- If you have multiple projects sharing the same database server, you may need to handle multiple domains in the hook
- The hook runs automatically when Certbot renews certificates (twice daily checks)
- Test the hook manually before relying on automatic renewal: `sudo /etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh`

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

## When to Use Automated vs. Manual Methods

### Use Automated Methods When:
- Setting up a standard deployment
- You want the quickest path to a working system
- You're comfortable with default configurations
- You're doing initial setup

**Automated commands:**
- `deploy -self-cert` or `deploy -get-cert` for NGINX certificates
- `init-db -root --confirm -self-cert` or `init-db -root --confirm -get-cert` for MySQL certificates

### Use Manual Methods When:
- You need custom certificate configurations
- You want to understand the underlying process
- You're troubleshooting certificate issues
- You need to set up the renewal hook (always manual)

**What automated methods handle:**
- Certificate generation/obtainment
- Directory creation
- File copying (for MySQL)
- Ownership and permissions
- NGINX/MySQL configuration

**What you still need to do manually:**
- Create and configure the MySQL certificate renewal hook script
- Custom certificate configurations (if needed)
- Advanced troubleshooting

## Install Config Values

The following SSL-related values go into `/root/.{project}-install.cnf`:

**For localhost deployment (no SSL/TLS):**
```ini
[install]
# TLS/SSL disabled for localhost
mysql_tls_enabled = 0
ssl_enabled = 0

# SSL paths still need to be set (even if not used)
mysql_ssl_dir = /etc/mysql/ssl
mysql_server_cert_path = /etc/mysql/ssl/server-cert.pem
mysql_server_key_path = /etc/mysql/ssl/server-key.pem
mysql_config_path = /etc/mysql/mysql.conf.d/mysqld.cnf
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem
```

**For public deployment (TLS/SSL enabled):**
```ini
[install]
# TLS/SSL enabled for public deployments
mysql_tls_enabled = 1
ssl_enabled = 1

# SSL paths (all configurable)
mysql_ssl_dir = /etc/mysql/ssl
mysql_server_cert_path = /etc/mysql/ssl/server-cert.pem
mysql_server_key_path = /etc/mysql/ssl/server-key.pem
mysql_config_path = /etc/mysql/mysql.conf.d/mysqld.cnf
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem

# NGINX webroot (for Let's Encrypt challenges)
webroot_dir = /var/www/html
```

**Note**: Both `ssl_ca_path` and `cache_ssl_ca_path` typically point to the same file (`/etc/mysql/ssl/ca.pem`) since both database subdomains use the same certificate. All paths are configurable and can be changed from their defaults.

## Verification

After setting up certificates (automated or manual), verify:

1. **NGINX certificates exist** (if `ssl_enabled = 1`):
   ```bash
   ls -la /etc/letsencrypt/live/example.com/
   ```
   Or for self-signed:
   ```bash
   ls -la /etc/nginx/ssl/example.com/
   ```

2. **MySQL SSL files exist** (only if `mysql_tls_enabled = 1`):
   ```bash
   ls -la /etc/mysql/ssl/
   ```
   Or use your configured `mysql_ssl_dir` path.

3. **MySQL SSL is configured** (only if `mysql_tls_enabled = 1`):
   ```bash
   grep -E "ssl-ca|ssl-cert|ssl-key" /etc/mysql/mysql.conf.d/mysqld.cnf
   ```
   Or use your configured `mysql_config_path`.

4. **MySQL can read SSL files** (only if `mysql_tls_enabled = 1`):
   ```bash
   sudo -u mysql ls -la /etc/mysql/ssl/
   ```

5. **Renewal hook exists** (only if using Let's Encrypt for MySQL with `mysql_tls_enabled = 1`):
   ```bash
   ls -la /etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh
   ```
   Verify it's executable and contains correct paths.

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

**For localhost deployments** (`mysql_tls_enabled = 0`, `ssl_enabled = 0`):
- No certificates needed
- Proceed directly to **Chapter 5: Installation**

**For public deployments** (`mysql_tls_enabled = 1` or `ssl_enabled = 1`):
- Set up certificates using automated methods (`-self-cert` or `-get-cert` flags)
- Create the MySQL renewal hook manually (if using Let's Encrypt for MySQL)
- Proceed to **Chapter 5: Installation**
- The installer will use the SSL CA paths you configured

