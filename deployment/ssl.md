# SSL Certificate Management

The SSL certificate management system handles Let's Encrypt certificate acquisition, renewal, and NGINX integration for Henhouse deployments.

## Prerequisites

Before setting up SSL certificates, you must have:
- NGINX installed and configured (see `http-nginx.md`)
- DNS configured to point domains to the server
- HTTP deployment completed (Stage 1) - see `http-nginx.md`
- Sudo/root privileges for Certbot operations

## Certificate Architecture

Henhouse uses **webroot mode** for all Let's Encrypt certificates:
- **Webroot Path**: `/var/www/html` (standardized across all certificates)
- **Challenge Location**: `/.well-known/acme-challenge/`
- **No Service Disruption**: NGINX remains running during certificate operations

### Why Webroot Mode?

Webroot mode is preferred over standalone mode because:
- No need to stop/start NGINX (avoids service disruption)
- Works seamlessly with existing NGINX configurations
- Allows automatic renewal without manual intervention
- Compatible with all domain types (main, admin, panel, db, cache)

## HTTP Redirect Block with ACME Challenge Exception

The HTTP-to-HTTPS redirect block includes an exception for Let's Encrypt ACME challenges:

```nginx
# HTTP - redirect to HTTPS (except ACME challenges)
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

**Key Features**:
- Serves ACME challenge files from `/var/www/html/.well-known/acme-challenge/` on HTTP (port 80)
- Redirects all other HTTP traffic to HTTPS
- Automatically includes `db.{domain}` and `cache.{domain}` subdomains for Henhouse sites
- Works for all domains (main, admin, panel, db, cache)

**Implementation**: `hh/deploy/http/nginx_config_helpers.py` - `generate_http_redirect_block()`

## Certificate Acquisition

### Initial Certificate Setup

For new certificates, use webroot mode with the standardized path:

```bash
sudo certbot certonly --webroot -w /var/www/html -d example.com -d www.example.com -d admin.example.com -d panel.example.com
```

**Parameters**:
- `--webroot`: Use webroot authentication mode
- `-w /var/www/html`: Webroot path (standardized)
- `-d <domain>`: Domain names to include in certificate

### Standardized Webroot Path

All certificates use `/var/www/html` as the webroot path:
- Simplifies NGINX configuration (single location block)
- Works for all domains and subdomains
- No need to match certificate webroot to site document root
- Challenge files are temporary and don't need to be in site directories

## Certificate Renewal

### Automatic Renewal

Certbot automatically renews certificates via systemd timer:
- Checks for expiring certificates twice daily
- Renews certificates that expire within 30 days
- Runs renewal hooks (pre, deploy, post) automatically

### Manual Renewal Testing

Test renewal process without actually renewing:

```bash
sudo certbot renew --dry-run
```

### Renewal Configuration

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

## NGINX Integration

### HTTP Deployment (Stage 1)

HTTP deployment includes ACME challenge location block:

```nginx
# Allow Let's Encrypt ACME challenges
location /.well-known/acme-challenge/ {
    root /var/www/html;
    try_files $uri =404;
}
```

This allows certificate acquisition before SSL deployment.

### SSL Deployment (Stage 2)

SSL deployment includes HTTP redirect block with ACME challenge exception (see above). This ensures:
- Certificates can be renewed without breaking the redirect
- Challenge files are accessible on HTTP (required for webroot validation)
- All other traffic is redirected to HTTPS

**Implementation**: `hh/deploy/http/http_deploy_ssl.py` - `create_nginx_ssl_config()`

## Certificate Locations

- **Live Certificates**: `/etc/letsencrypt/live/{domain}/`
  - `fullchain.pem`: Certificate chain
  - `privkey.pem`: Private key
  - `cert.pem`: Certificate
  - `chain.pem`: Certificate chain (intermediate)
- **Archive**: `/etc/letsencrypt/archive/{domain}/` - Historical certificate versions
- **Renewal Configs**: `/etc/letsencrypt/renewal/{domain}.conf` - Renewal settings

## Renewal Hooks

Certbot supports renewal hooks in `/etc/letsencrypt/renewal-hooks/`:
- **pre/**: Scripts run before renewal
- **deploy/**: Scripts run after successful renewal
- **post/**: Scripts run after renewal (success or failure)

See `mysql.md` for MySQL SSL certificate renewal hook.

## Troubleshooting

### Certificate Renewal Fails with 404

**Problem**: ACME challenge files return 404 errors

**Solutions**:
1. Verify NGINX serves `/.well-known/acme-challenge/` from `/var/www/html
2. Check renewal config uses correct webroot path
3. Ensure `/var/www/html/.well-known/acme-challenge/` directory exists and is writable

### Certificate Renewal Fails with 401

**Problem**: ACME challenge files return 401 (Unauthorized) errors

**Solutions**:
1. Verify HTTP Basic Auth is not blocking `/.well-known/acme-challenge/`
2. Check that ACME challenge location block is before auth blocks in NGINX config
3. Ensure challenge files are served on HTTP, not HTTPS

### Port 80 Conflict

**Problem**: "Could not bind TCP port 80" error

**Solutions**:
1. Ensure certificate uses webroot mode (not standalone)
2. Check NGINX is running and using port 80
3. Verify no other service is using port 80

## Integration with Other Systems

- **HTTP/NGINX Deployment** (`http-nginx.md`): SSL deployment includes ACME challenge exception in HTTP redirect block
- **MySQL SSL** (`mysql.md`): Database certificates use renewal hooks to update MySQL SSL certificates
- **Database Subdomains**: `db.{domain}` and `cache.{domain}` automatically included in HTTP redirect blocks for ACME challenges

## Best Practices

1. **Standardize Webroot Path**: Use `/var/www/html` for all certificates
2. **Test Renewals**: Run `certbot renew --dry-run` regularly to verify renewal process
3. **Monitor Expiration**: Check certificate expiration dates periodically
4. **Document Custom Hooks**: Document any custom renewal hooks in deployment documentation
5. **Use Webroot Mode**: Always use webroot mode for new certificates (avoid standalone mode)

