# Chapter 1: DNS, NGINX, and Domain Setup

## System Requirements and Hardware

### Deployment Box vs Developer Box

**Deployment Box**: A Linux server where Henhouse runs in production. This is where you install Henhouse, run the database, serve web requests, and host your content. Deployment boxes are designed to be:
- Accessible over the network (local-only or remote with static IP)
- Running Linux server OS (Ubuntu Server recommended)
- Capable of running all services (NGINX, MySQL, Flask daemons, maintenance daemons)
- Designed to be part of a cluster of multiple deployment boxes for optimization

**Developer Box**: Your laptop, desktop, or development machine (Windows, Mac, or Linux) where you write code and use your IDE. The developer box:
- Does NOT run Henhouse installation
- Connects to deployment boxes via SSH and MCP
- Runs Cursor or other IDEs for development
- Should NOT be used as a deployment box (Mac laptops can host NGINX, but are not suitable for full Henhouse deployment)

### Hardware Requirements

**Minimum Requirements** (for single-box deployment):
- **CPU**: Any modern x86_64 processor
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 256GB minimum, 512GB recommended
- **Network**: Ethernet connection (for remote access, static IP recommended)

**Test Hardware**:
Henhouse is tested and developed on:
- **Model**: B-Link mini S mini PC
- **CPU**: Intel N150 processor
- **RAM**: 16GB
- **Storage**: 512GB SSD
- **OS**: Ubuntu Server 24.x (24.04 LTS)

**Cluster Architecture**:
Henhouse is designed to be deployed across multiple deployment boxes in a cluster configuration. You can start with a single box and expand to 4-5 boxes (or more) for optimization and load distribution. Each box can run different services or multiple Henhouse installations.

### Operating System

**Tested OS**: Ubuntu Server 24.x (24.04 LTS)

**Compatibility**: Should work on most Linux distributions (Debian, Ubuntu variants, etc.), but Ubuntu Server is recommended and all installation steps are written for Ubuntu/Debian systems.

### Initial System Setup

After installing Ubuntu Server, update the system:

```bash
sudo apt update
sudo apt upgrade -y
```

**Install Required System Packages**:

Before proceeding with Henhouse installation, install these system packages:

```bash
# Python and pip
sudo apt install python3 python3-pip -y

# Git (for cloning the repository)
sudo apt install git -y

# MySQL client libraries (required for pymysql)
sudo apt install default-libmysqlclient-dev -y

# NGINX (web server - required for HTTP deployment)
sudo apt install nginx -y

# MySQL server (if running database on this box)
sudo apt install mysql-server -y
```

**Note on Package Management**:
- Use `apt` for system packages (Python, Git, NGINX, MySQL, etc.)
- Use `pip3` for Python packages (Flask, pymysql, etc.)
- Python packages are listed in `requirements.txt` and installed with `pip3 install -r requirements.txt`

### Installation Scope

This documentation covers installation for:
- **Local-only deployment**: Single box on local network, accessible via local IP
- **Remote deployment**: Box with static IP, accessible over the internet
- **Single-box deployment**: All services (NGINX, MySQL, Flask) running on one box
- **Multi-box cluster**: Services distributed across multiple deployment boxes (advanced setup)

The installation process is the same for both local-only and remote deployments. The main difference is DNS configuration (local-only may use `/etc/hosts` instead of public DNS records).

## Quick Reference

Before setting up your Henhouse installation, you need to prepare the following infrastructure components. This quick reference lists all the information you'll need to track and where it will be used.

### Information to Track

| Component | What You Need | Where It's Used |
|-----------|---------------|-----------------|
| **Main Domain** | Your primary domain (e.g., `example.com`) | Install config: not directly stored, but used for DNS records and NGINX configs |
| **WWW Subdomain** | `www.example.com` | DNS A record, NGINX server block |
| **Admin Subdomain** | `admin.example.com` | DNS A record, NGINX server block with HTTP Basic Auth |
| **Panel Subdomain** | `panel.example.com` | DNS A record, NGINX server block with HTTP Basic Auth |
| **Database Subdomain** | `db.example.com` | DNS A record, MySQL SSL certificate, install config `db_host` |
| **Cache Subdomain** | `cache.example.com` | DNS A record, MySQL SSL certificate, install config `cache_host` |
| **Static IP Address** | Your deployment server's static IP | DNS A records, MySQL root user grants |
| **NGINX Config Path** | `/etc/nginx/sites-available/{domain}` | Installer expects NGINX configs here |
| **NGINX Enabled Path** | `/etc/nginx/sites-enabled/{domain}` | Installer creates symlinks here |
| **Webroot Path** | `/var/www/html` | Let's Encrypt ACME challenges, SSL certificate webroot |
| **htpasswd Files** | `/var/www/.htpasswd_admin`, `/var/www/.htpasswd_panel` | Created by installer, used by NGINX for Basic Auth |

### Expected File Paths

The installer and deployment system expect the following paths to exist or be configured:

**NGINX Configuration:**
- `/etc/nginx/sites-available/{domain}` - NGINX site configuration files
- `/etc/nginx/sites-enabled/{domain}` - Symlinks to enabled sites
- NGINX must be installed and running

**Web Server Directories:**
- `/var/www/html` - Webroot for Let's Encrypt ACME challenges
- `/var/www/.htpasswd_admin` - HTTP Basic Auth for admin subdomain (created by installer)
- `/var/www/.htpasswd_panel` - HTTP Basic Auth for panel subdomain (created by installer)

**Project Directories (created by installer):**
- `/srv/{project_name}/` - Main project deployment directory
- `/srv/{project_name}/git/{project_name}.git` - Bare git repository
- `/srv/images/{project_name}/` - Image storage
- `/srv/files/{project_name}/` - File storage
- `/srv/audio/{project_name}/` - Audio storage
- `/srv/video/{project_name}/` - Video storage

## DNS Prerequisites

### Required DNS Records

You need to create DNS A records pointing to your deployment server's static IP address:

| Record Type | Name | Value | Purpose |
|-------------|------|-------|---------|
| A | `@` (or root domain) | `your.static.ip.address` | Main domain access |
| A | `www` | `your.static.ip.address` | WWW subdomain |
| A | `admin` | `your.static.ip.address` | Admin subdomain (HTTP Basic Auth) |
| A | `panel` | `your.static.ip.address` | Panel subdomain (HTTP Basic Auth) |
| A | `db` | `your.static.ip.address` | Database subdomain (MySQL SSL) |
| A | `cache` | `your.static.ip.address` | Cache subdomain (MySQL SSL) |

**Note**: For your first installation, set `db` and `cache` to point to your database server. For subsequent installations on the same server, reuse the same `db` and `cache` subdomains (they'll share the same database server).

### DNS Setup Timeline

DNS records should be configured **before** running the installer. The installer will need:
- `db_host` = `db.yourdomain.tld` (for install config)
- `cache_host` = `cache.yourdomain.tld` (for install config)

These values are used in the install config file (`/root/.{project}-install.cnf`) and must match your DNS configuration.

## NGINX Prerequisites

### Installation

NGINX must be installed and running on your deployment server before you can deploy Henhouse sites. The installer does not install NGINX for you.

**Installation commands** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Expected Directory Structure

The installer expects NGINX to use the standard Debian/Ubuntu configuration structure:

- **Site configurations**: `/etc/nginx/sites-available/{domain}`
- **Enabled sites**: `/etc/nginx/sites-enabled/{domain}` (symlinks to `sites-available`)
- **Main config**: `/etc/nginx/nginx.conf` (typically includes `sites-enabled/*`)

## Technical Details: NGINX Configuration Structure

The HTTP deployment system generates NGINX configuration files with the following structure:

**HTTP Configuration (Stage 1)**:
- Three server blocks: main domain (guest tier), admin subdomain, panel subdomain
- Port 80 (HTTP only)
- ACME challenge location block for Let's Encrypt
- Static file locations from whitelists
- Security headers, rate limiting, hidden file blocking
- Flask proxy configuration to localhost ports

**HTTPS Configuration (Stage 2)**:
- HTTP-to-HTTPS redirect block (port 80)
- Three HTTPS server blocks (port 443) with SSL certificates
- HTTP/2 enabled for HTTPS
- HSTS header included
- Same features as HTTP plus SSL/TLS encryption

**Deployment Markers**: Config files include "Generated by henhouse deploy-http system" or "Generated by henhouse deploy-ssl system" markers. The `http-remove` command validates these markers before deleting configs (safety feature).

### Webroot Directory

The installer expects `/var/www/html` to exist and be writable for Let's Encrypt ACME challenges:

```bash
sudo mkdir -p /var/www/html
sudo chown www-data:www-data /var/www/html
sudo chmod 755 /var/www/html
```

This directory is used for:
- Let's Encrypt ACME challenge files (`.well-known/acme-challenge/`)
- SSL certificate validation during initial setup

## Domain Configuration

### First Installation vs. Subsequent Installations

**First Installation:**
- Set `db_host` and `cache_host` in install config to `db.yourdomain.tld` and `cache.yourdomain.tld`
- These subdomains should point to your database server's IP address
- SSL certificates will be needed for these subdomains (see Chapter 3)

**Subsequent Installations:**
- Reuse the same `db_host` and `cache_host` values from your first installation
- All installations on the same server share the same database server
- SSL certificates for `db` and `cache` subdomains are shared across installations

### Domain Naming Convention

The installer uses your project name to generate subdomains:
- Main domain: `{domain}` (e.g., `example.com`)
- Admin: `admin.{domain}`
- Panel: `panel.{domain}`
- Database: `db.{domain}` (shared across installations)
- Cache: `cache.{domain}` (shared across installations)

## Verification

Before proceeding to installation, verify:

1. **DNS Records**: All 6 A records (root, www, admin, panel, db, cache) point to your server's static IP
   ```bash
   dig +short example.com
   dig +short www.example.com
   dig +short admin.example.com
   dig +short panel.example.com
   dig +short db.example.com
   dig +short cache.example.com
   ```

2. **NGINX Status**: NGINX is installed and running
   ```bash
   sudo systemctl status nginx
   ```

3. **Webroot Directory**: `/var/www/html` exists and is writable
   ```bash
   ls -la /var/www/html
   ```

4. **Static IP**: You know your deployment server's static IP address (for DNS records and MySQL configuration)

## Next Steps

Once DNS and NGINX are configured:
1. Proceed to **Chapter 2: MySQL Server Setup** to configure your database server
2. Then **Chapter 3: SSL Certificates** to set up Let's Encrypt certificates
3. Finally **Chapter 5: Installation** to run the installer

