# DNS Configuration

This document covers the DNS (Domain Name System) setup requirements for deploying Henhouse projects.

## Prerequisites

Before installing Henhouse, you must have:

1. **At least one top-level domain** that you own and control
   - Ideally, one domain per project (e.g., `henhouse.ai` for henhouse, `foxhouse.ai` for foxhouse)
   - The system is designed assuming you have multiple top-level domains available

2. **A static IP address** for your deployment server
   - The server must be reachable from the internet
   - All DNS records will point to this same static IP address

3. **DNS management access** to configure A records for your domain(s)

## Required DNS Records

For each project, you need to create the following A records, all pointing to your server's static IP address:

### Main Domain Records

- `{domain}` - The main domain (e.g., `henhouse.ai`)
- `www.{domain}` - WWW subdomain (e.g., `www.henhouse.ai`)

### Application Subdomains

- `admin.{domain}` - Admin interface subdomain (e.g., `admin.henhouse.ai`)
- `panel.{domain}` - Panel interface subdomain (e.g., `panel.henhouse.ai`)

### Database Subdomains

- `db.{domain}` - Main database server (e.g., `db.henhouse.ai`)
- `cache.{domain}` - Cache database server (e.g., `cache.henhouse.ai`)

**Note**: If you're setting up multiple projects on the same server, they can share the same database servers. In that case:
- First project: Use `db.{firstdomain}` and `cache.{firstdomain}`
- Second+ projects: Use the same `db.{firstdomain}` and `cache.{firstdomain}` as the first project

## DNS Setup Timeline

DNS records should be configured **before** running the installer, as the installer will:
1. Validate that database hostnames are specified in the config
2. Create configuration files that reference these domains
3. Expect these domains to be resolvable when database connections are attempted

However, SSL certificates can be set up **after** installation (see `ssl.md` for details). The installer will accept SSL certificate paths even if the files don't exist yet, allowing you to set up certificates after installation completes.

## Example DNS Configuration

For a project using `henhouse.ai`:

```
henhouse.ai          A    <your-static-ip>
www.henhouse.ai      A    <your-static-ip>
admin.henhouse.ai    A    <your-static-ip>
panel.henhouse.ai    A    <your-static-ip>
db.henhouse.ai       A    <your-static-ip>
cache.henhouse.ai    A    <your-static-ip>
```

For a second project using `foxhouse.ai` (sharing the same database servers):

```
foxhouse.ai          A    <your-static-ip>
www.foxhouse.ai      A    <your-static-ip>
admin.foxhouse.ai    A    <your-static-ip>
panel.foxhouse.ai    A    <your-static-ip>
# Note: db and cache use the first project's domains
# db.henhouse.ai      (already configured above)
# cache.henhouse.ai   (already configured above)
```

## Verification

After setting up DNS records, verify they resolve correctly:

```bash
# Check main domain
dig henhouse.ai +short

# Check subdomains
dig www.henhouse.ai +short
dig admin.henhouse.ai +short
dig panel.henhouse.ai +short
dig db.henhouse.ai +short
dig cache.henhouse.ai +short

# All should return your static IP address
```

## Related Documentation

- `mysql.md` - MySQL database server setup
- `ssl.md` - SSL certificate configuration
- `http-nginx.md` - NGINX web server configuration

