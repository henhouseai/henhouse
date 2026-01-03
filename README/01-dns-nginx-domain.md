# Chapter 1: DNS, NGINX, and Domain Setup

## System Requirements and Hardware

### Deployment Box vs Developer Box

**Deployment Box**: A Linux server where Henhouse runs in production. This is where you install Henhouse, run the database, serve web requests, and host your content. Deployment boxes are designed to be:
- Accessible over the network (local-only or remote with static IP)
- Running Linux server OS (Ubuntu Server recommended)
- Capable of running all services (NGINX, MySQL, Flask daemons, maintenance daemons)
- Designed to support cluster configurations (cluster deployment automation is under development)

**Developer Box**: Your laptop, desktop, or development machine (Windows, Mac, or Linux) where you write code and use your IDE. The developer box:
- Does NOT run Henhouse installation (system is designed with separate boxes in mind)
- Connects to deployment boxes via SSH and MCP
- Runs Cursor or other IDEs for development
- **Note**: Theoretically, the developer box and deployment box could be the same machine (e.g., on a Linux system), but this configuration has not been tested. All testing and design has been done with separate boxes in mind.

### Hardware Requirements

Henhouse has minimal hardware requirements and should run on most systems, including older hardware or even a Raspberry Pi (though performance may vary). More RAM is always beneficial, and more storage is recommended if you plan to host many files.

**Test Hardware**:
Henhouse is currently tested and developed on:
- **Model**: B-Link mini S mini PC
- **CPU**: Intel N150 processor
- **RAM**: 16GB
- **Storage**: 512GB SSD
- **OS**: Ubuntu Server 24.x (24.04 LTS)

This hardware serves as our reference configuration. As cluster development progresses, the cluster deployment architecture will consist of multiple copies of this same hardware configuration. The system is designed to scale horizontally by adding duplicate boxes of this specification.

**Cluster Architecture** (Future Development):
**Note**: Cluster deployment automation is still under development. The scope of this documentation and the installation scripts currently covers **single-box deployment only**, where NGINX, the main database, the cache database, and the future history database all run on the same box.

The system is designed to support cluster configurations, and the envisioned architecture includes:
- **Cluster of 5 boxes**: One NGINX/web server box, one main database box, one cache database box, one history database box (future), and one backup/archive box for automatically archiving state from all other drives
- **Expansion options**: Additional boxes can be added (e.g., a 6th box could be another NGINX server pointing to the same database boxes, or hybrid configurations where a new box has its own main and cache databases but shares the history database and backup box with the existing cluster)

These cluster configurations are theoretically possible to set up manually, but the automated installation process does not yet support multi-box deployments. All instructions in this documentation assume a single-box deployment where all services run on the same machine.

### Deployment Modes

Henhouse can be deployed in two main modes:

**Local-Only Deployment**:
- Single box on local network, accessible via local IP address
- Uses `/etc/hosts` on client machines to map domain names to local IP addresses instead of public DNS records
- Ideal for testing and development
- Can be configured to bind to specific local IP addresses to prevent external access

**Public-Facing Deployment**:
- Box with static IP, accessible over the internet
- Requires public DNS records pointing to your server
- Can be configured as public (anyone can access guest tier) or private (guest tier behind password)
- Admin and panel subdomains are always behind HTTP Basic Auth passwords

**Deployment Configuration Options**:

The system provides several configuration options that affect how your deployment behaves:

- **SSL/TLS**: Enable or disable HTTPS via `ssl_enabled` setting in install config (default: enabled). For local deployments, HTTP-only mode is simpler for initial testing.

- **Guest Access Control**: Set `htaccess_guest_password` in install config to require a password for the main site (guest tier). Leave blank for public access. Admin and panel subdomains always require passwords.

- **Local IP Binding**: For local deployments, configure `local_allow_block` to restrict NGINX to specific IP addresses (e.g., `192.168.1.` for subnet, `192.168.1.100` for specific IP), preventing external access even if the server is public-facing.

- **SSL Certificates**: For public deployments, you can use Let's Encrypt certificates (automatic) or self-signed certificates (for testing). For local deployments, self-signed certificates or HTTP-only mode are recommended.

The installation process is the same for both local-only and remote deployments. The main difference is DNS configuration and certificate management. You will setup these config flags during the installation.

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

Before proceeding with Henhouse installation, install all required system packages and Python dependencies:

```bash
# Install all system packages and Python dependencies in one command
sudo apt install python3 python3-pip git default-libmysqlclient-dev nginx mysql-server apache2-utils python3-flask python3-pymysql python3-psutil python3-mutagen python3-pil ffmpeg -y
```

**What this installs**:
- **Python 3** - Python interpreter (usually pre-installed)
- **python3-pip** - Python package manager (optional, for developer boxes)
- **Git** - Version control (for cloning henhouse repository)
- **default-libmysqlclient-dev** - MySQL client libraries (required for pymysql)
- **NGINX** - Web server (required for HTTP deployment - see Chapter 8)
- **MySQL server** - Database server (required for database setup - see Chapter 2)
- **apache2-utils** - Provides `htpasswd` command (required for HTTP Basic Auth - see Chapter 8)
- **Python dependencies** - Flask, pymysql, psutil, mutagen, Pillow (all available as apt packages)
- **ffmpeg** - Audio/video processing (includes ffprobe)

**Note**: NGINX and MySQL are **required** for full Henhouse deployment. The dependency checker (`python3 hen.py dependency-list`) only checks Python packages, not system services like NGINX or MySQL.

**Note on Package Management**:
- Use `apt` for all packages (system packages and Python packages)
- Python dependencies are available as apt packages: `python3-flask`, `python3-pymysql`, `python3-psutil`, `python3-mutagen`, `python3-pil`
- Install all dependencies with: `sudo apt install python3-flask python3-pymysql python3-psutil python3-mutagen python3-pil ffmpeg -y`
- `requirements.txt` is provided for developer boxes or systems where apt packages aren't available

### Installation Scope

This documentation covers:
- **Single-box deployment**: All services (NGINX, MySQL, Flask) running on one box (fully supported by installation scripts)
- **Multi-box cluster**: Services distributed across multiple deployment boxes (system is designed to support this, but automated installation for multi-box clusters is not yet implemented - see "Cluster Architecture" section above)

See "Deployment Modes" section above for details on local-only vs public-facing deployments.

## Quick Reference

Before setting up your Henhouse installation, you need to prepare the following infrastructure components. This quick reference lists all the information you'll need to track and where it will be used.

### Information to Track

The following information is stored in the install config file (located at `/root/.{project_name}-install.cnf`):

| Component | Config Key | Default Value | Description |
|-----------|------------|---------------|-------------|
| **Domain** | `domain` | `example.local` | Primary domain for web deployment (use `.local` for local network deployments) |
| **Database Host** | `db_host` | `localhost` | MySQL main database host (subdomain for public deployments) |
| **Cache Host** | `cache_host` | `localhost` | MySQL cache database host (subdomain for public deployments) |
| **SSL Enabled** | `ssl_enabled` | `0` | Enable SSL/TLS (1 = enabled, 0 = disabled) |
| **NGINX Sites Available** | `nginx_sites_available` | `/etc/nginx/sites-available` | Directory for NGINX site config files |
| **NGINX Sites Enabled** | `nginx_sites_enabled` | `/etc/nginx/sites-enabled` | Directory for NGINX enabled site symlinks |
| **Webroot Directory** | `webroot_dir` | `/var/www/html` | Directory for Let's Encrypt ACME challenges |
| **SSL Cert Dir (Let's Encrypt)** | `ssl_cert_dir_letsencrypt` | `/etc/letsencrypt/live` | Let's Encrypt certificate directory |
| **SSL Cert Dir (Self-Signed)** | `ssl_cert_dir_self_signed` | `/etc/nginx/ssl` | Self-signed certificate directory |
| **SSL CA Path** | `ssl_ca_path` | `/etc/mysql/ssl/ca.pem` | MySQL SSL CA certificate path |
| **Cache SSL CA Path** | `cache_ssl_ca_path` | `/etc/mysql/ssl/ca.pem` | Cache MySQL SSL CA certificate path |
| **Local IP Binding** | `local_allow_block` | `192.168.1.` | IP pattern for local-only deployments |
| **Flask Start Port** | `flask_start_port` | `5001` | Starting port for Flask daemons (reserves 100 ports) |
| **Entry Script Name** | `entry_point_script_name` | `hen` | Name of the entry point script |
| **Passwords** | Various | `CHANGE_ME` | MySQL root passwords, application passwords, HTTP Basic Auth passwords |

**Additional Information (not in config file, but needed for setup):**
- **Subdomains**: `www.{domain}`, `admin.{domain}`, `panel.{domain}`, `db.{domain}`, `cache.{domain}` - Used for DNS records and NGINX configs
- **Static IP Address**: Your deployment server's static IP - Used for DNS A records and MySQL root user grants

### File Paths

**Hardcoded Paths (not configurable):**
- `/srv/{project_name}/` - Main project deployment directory (hardcoded)
- `/srv/{project_name}/git/{project_name}.git` - Bare git repository (hardcoded)
- `/srv/images/{project_name}/` - Image storage (hardcoded)
- `/srv/files/{project_name}/` - File storage (hardcoded)
- `/srv/audio/{project_name}/` - Audio storage (hardcoded)
- `/srv/video/{project_name}/` - Video storage (hardcoded)
- `/root/.{project_name}-install.cnf` - Install config file location (hardcoded)

**Configurable Paths (default values shown, can be changed in install config):**
- `nginx_sites_available` - Default: `/etc/nginx/sites-available/{domain}` - NGINX site configuration files
- `nginx_sites_enabled` - Default: `/etc/nginx/sites-enabled/{domain}` - Symlinks to enabled sites
- `webroot_dir` - Default: `/var/www/html` - Webroot for Let's Encrypt ACME challenges
- `ssl_cert_dir_letsencrypt` - Default: `/etc/letsencrypt/live` - Let's Encrypt certificates
- `ssl_cert_dir_self_signed` - Default: `/etc/nginx/ssl` - Self-signed certificates
- `htpasswd_dir` - Default: `/var/www` - HTTP Basic Auth htpasswd directory (where `.htpasswd_guest`, `.htpasswd_admin`, `.htpasswd_panel` files are stored)
- `ssl_ca_path` - Default: `/etc/mysql/ssl/ca.pem` - MySQL SSL CA certificate
- `cache_ssl_ca_path` - Default: `/etc/mysql/ssl/ca.pem` - Cache MySQL SSL CA certificate

## DNS Prerequisites

### Local-Only Deployment: /etc/hosts Configuration

For local-only deployments, you need to configure `/etc/hosts` on each client machine (developer box, etc.) to map domain names to your deployment server's IP address. This replaces public DNS records.

**Example 1: Deployment box with static IP address**

If your deployment box has a static IP address (e.g., `203.0.113.10`), add entries to `/etc/hosts` on your client machines:

```
203.0.113.10    example.local
203.0.113.10    www.example.local
203.0.113.10    admin.example.local
203.0.113.10    panel.example.local
203.0.113.10    db.example.local
203.0.113.10    cache.example.local
```

**Example 2: Deployment box with local network IP address**

If your deployment box has a local network IP address (e.g., `192.168.1.100`), add entries to `/etc/hosts` on your client machines:

```
192.168.1.100    mysite.local
192.168.1.100    www.mysite.local
192.168.1.100    admin.mysite.local
192.168.1.100    panel.mysite.local
192.168.1.100    db.mysite.local
192.168.1.100    cache.mysite.local
```

**Important Notes**:
- You must add these entries to `/etc/hosts` on **every client machine** that needs to access the deployment (developer box, other computers on the network, etc.)
- The domain names you use (e.g., `example.local`, `mysite.local`) are arbitrary - you can use any domain name you want
- All 6 subdomains (root, www, admin, panel, db, cache) must be configured
- The IP address must be the deployment server's IP address (static IP or local network IP)

### Public-Facing Deployment: Required DNS Records

For public-facing deployments, you need to create DNS A records pointing to your deployment server's static IP address:

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

**For local-only deployments**: Configure `/etc/hosts` on all client machines **before** running the installer.

**For public-facing deployments**: DNS records should be configured **before** running the installer.

The installer will need:
- `db_host` = `db.yourdomain.tld` (or `db.yourdomain.local` for local deployments)
- `cache_host` = `cache.yourdomain.tld` (or `cache.yourdomain.local` for local deployments)

These values are used in the install config file (`/root/.{project}-install.cnf`) and must match your DNS configuration (public DNS records) or `/etc/hosts` configuration (local-only deployments).

## NGINX Prerequisites

### Installation

NGINX must be installed on your deployment server before you can deploy Henhouse sites. NGINX is included in the package list in the "Initial System Setup" section above. After installation, NGINX should automatically start. You can verify it's running by accessing your server's IP address in a web browser - you should see the NGINX default welcome page.

The NGINX configuration directory paths (`nginx_sites_available` and `nginx_sites_enabled`) are configurable in the install config file (see Chapter 5). By default, they use the standard Debian/Ubuntu paths: `/etc/nginx/sites-available` and `/etc/nginx/sites-enabled`.

## Technical Details: NGINX Configuration Structure

The HTTP deployment system generates NGINX configuration files with the following structure:

**HTTP Configuration (Stage 1)**:
- Three server blocks: main domain (guest tier), admin subdomain, panel subdomain
- Port 80 (HTTP only)
- ACME challenge location block for Let's Encrypt
- Static file locations from whitelists
- Security headers, hidden file blocking
- Flask proxy configuration to localhost ports

**HTTPS Configuration (Stage 2)**:
- HTTP-to-HTTPS redirect block (port 80)
- Three HTTPS server blocks (port 443) with SSL certificates
- HTTP/2 enabled for HTTPS
- HSTS header included
- Same features as HTTP plus SSL/TLS encryption

### Webroot Directory

The webroot directory (configurable in the install config file as `webroot_dir`, default: `/var/www/html`) must exist and be writable for Let's Encrypt ACME challenges:

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

3. **MySQL Status**: MySQL server is installed and running (if running database on this box)
   ```bash
   sudo systemctl status mysql
   ```

4. **Webroot Directory**: `/var/www/html` exists and is writable
   ```bash
   ls -la /var/www/html
   ```

5. **Static IP**: You know your deployment server's static IP address (for DNS records and MySQL configuration)

## Next Steps

Once DNS and NGINX are configured:
1. Proceed to **Chapter 2: MySQL Server Setup** to configure your database server
2. Then **Chapter 3: SSL Certificates** to set up Let's Encrypt certificates
3. Finally **Chapter 5: Installation** to run the installer

