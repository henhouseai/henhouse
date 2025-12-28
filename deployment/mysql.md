# MySQL SSL Configuration

The MySQL SSL configuration system manages SSL certificates for MySQL database connections, including automatic certificate renewal and MySQL service restart.

## Prerequisites

Before setting up MySQL SSL, you must have:
- MySQL server installed and running
- Let's Encrypt certificate for database subdomain (see `ssl.md`)
- Sudo/root privileges for file operations and MySQL service management
- SSL certificate renewal hook configured (see below)

## MySQL SSL Architecture

MySQL SSL uses Let's Encrypt certificates for database subdomains:
- **Certificate Domain**: `db.{project_domain}` (e.g., `db.henhouse.ai`)
- **Certificate Location**: `/etc/letsencrypt/live/db.{domain}/`
- **MySQL SSL Directory**: `/etc/mysql/ssl/`
- **Automatic Renewal**: Certbot renewal hook updates MySQL certificates automatically

### Why Separate Database Certificates?

Database subdomains (`db.{domain}`, `cache.{domain}`) use separate certificates because:
- Database connections require SSL certificates
- Certificates must be accessible to MySQL process
- Renewal must update MySQL configuration automatically
- MySQL cannot use symlinks to Let's Encrypt certificates (permission issues)

## Certificate File Mapping

Let's Encrypt certificates are copied (not symlinked) to MySQL SSL directory:

| Let's Encrypt File | MySQL SSL File | Purpose |
|-------------------|----------------|---------|
| `fullchain.pem` | `ca.pem` | Certificate Authority chain (full chain including server cert) |
| `cert.pem` | `server-cert.pem` | Server certificate |
| `privkey.pem` | `server-key.pem` | Private key |

**Why Copy Instead of Symlink?**
- MySQL process needs proper file permissions
- Symlinks can cause permission issues during renewal
- Direct file access is more reliable for MySQL

## Initial Setup

### 1. Create MySQL SSL Directory

```bash
sudo mkdir -p /etc/mysql/ssl
```

### 2. Copy Certificates

Copy certificates from Let's Encrypt to MySQL SSL directory:

```bash
sudo cp -L /etc/letsencrypt/live/db.henhouse.ai/fullchain.pem /etc/mysql/ssl/ca.pem
sudo cp -L /etc/letsencrypt/live/db.henhouse.ai/cert.pem /etc/mysql/ssl/server-cert.pem
sudo cp -L /etc/letsencrypt/live/db.henhouse.ai/privkey.pem /etc/mysql/ssl/server-key.pem
```

**Note**: 
- `-L` flag dereferences symlinks (copies actual files, not symlinks)
- Use `fullchain.pem` for `ca.pem` (includes full certificate chain including server certificate)

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

Certbot renewal hook automatically updates MySQL certificates when Let's Encrypt certificate is renewed:

**Location**: `/etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh`

**Script Contents**:
```bash
#!/bin/bash
# Copy renewed certificates to MySQL SSL directory and restart MySQL

cp -L /etc/letsencrypt/live/db.henhouse.ai/fullchain.pem /etc/mysql/ssl/ca.pem
cp -L /etc/letsencrypt/live/db.henhouse.ai/cert.pem /etc/mysql/ssl/server-cert.pem
cp -L /etc/letsencrypt/live/db.henhouse.ai/privkey.pem /etc/mysql/ssl/server-key.pem

chown mysql:mysql /etc/mysql/ssl/*
chmod 644 /etc/mysql/ssl/ca.pem
chmod 644 /etc/mysql/ssl/server-cert.pem
chmod 600 /etc/mysql/ssl/server-key.pem

systemctl restart mysql
```

**Note**: Uses `fullchain.pem` for `ca.pem` to include the full certificate chain.

### Hook Execution

The renewal hook runs automatically:
- **When**: After successful certificate renewal
- **Trigger**: Certbot `deploy` hook (runs after renewal completes)
- **Location**: `/etc/letsencrypt/renewal-hooks/deploy/`
- **Permissions**: Must be executable (`chmod +x`)

### Testing Renewal Hook

Test the renewal hook manually:

```bash
sudo /etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh
```

Or test full renewal process:

```bash
sudo certbot renew --dry-run
```

## Certificate Acquisition for Database Subdomains

### Using Webroot Mode

Database subdomains use webroot mode (same as other certificates):

```bash
sudo certbot certonly --webroot -w /var/www/html -d db.henhouse.ai -d cache.henhouse.ai
```

**Requirements**:
- NGINX must serve `/.well-known/acme-challenge/` from `/var/www/html` for these domains
- HTTP redirect block must include `db.{domain}` and `cache.{domain}` in server_name
- See `ssl.md` for HTTP redirect block configuration

### NGINX Configuration

The HTTP redirect block automatically includes database subdomains:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name henhouse.ai www.henhouse.ai admin.henhouse.ai panel.henhouse.ai db.henhouse.ai cache.henhouse.ai;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```

**Implementation**: `hh/deploy/http/nginx_config_helpers.py` - `generate_http_redirect_block()` automatically adds `db.{domain}` and `cache.{domain}` subdomains.

## File Locations

- **Let's Encrypt Certificates**: `/etc/letsencrypt/live/db.{domain}/`
- **MySQL SSL Directory**: `/etc/mysql/ssl/`
- **Renewal Hook**: `/etc/letsencrypt/renewal-hooks/deploy/copy-mysql-certs.sh`
- **MySQL Config**: `/etc/mysql/mysql.conf.d/mysqld.cnf` (primary location on Ubuntu/Debian)

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

### SSL Verification Warning

**Problem**: MySQL error log shows warning: "Server SSL certificate doesn't verify: unable to get local issuer certificate"

**Explanation**: This is a **harmless warning**. MySQL is still using SSL encryption correctly. The warning occurs because MySQL cannot verify the certificate chain against its local CA store, but the certificate chain is valid and SSL connections are encrypted.

**Solutions**:
1. **Ignore the warning** - SSL is working correctly, this is just a verification message
2. Verify SSL is working: `SHOW STATUS LIKE 'Ssl_server_not_after';` should show your certificate expiration date
3. If desired, try using `chain.pem` instead of `fullchain.pem` for `ca.pem` (may or may not resolve the warning)

## Integration with Other Systems

- **SSL Certificate Management** (`ssl.md`): Database certificates use same webroot mode and renewal process
- **HTTP/NGINX Deployment** (`http-nginx.md`): HTTP redirect blocks include database subdomains for ACME challenges
- **Database Deployment** (`database.md`): MySQL SSL configuration is separate from database initialization

## Best Practices

1. **Use Webroot Mode**: Database certificates use webroot mode (not standalone) to avoid NGINX disruption
2. **Copy, Don't Symlink**: Copy certificate files to MySQL directory (permission issues with symlinks)
3. **Test Renewal Hooks**: Regularly test renewal hooks with `certbot renew --dry-run`
4. **Monitor MySQL Logs**: Check MySQL error logs after certificate renewal
5. **Document Custom Domains**: Update renewal hook script if using different domain names

