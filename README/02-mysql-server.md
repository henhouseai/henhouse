# Chapter 2: MySQL Server Setup

## Quick Reference

Before installing Henhouse, you need a MySQL server. For localhost deployments, plain text connections are supported (TLS disabled by default). For public deployments, TLS/SSL is recommended. This quick reference lists what information you need to track and where it's used.

### Information to Track

| Component | Config Key | Default Value | Where It's Used |
|-----------|-----------|---------------|-----------------|
| **Database Host** | `db_host` | `localhost` | Database connection hostname |
| **Cache Host** | `cache_host` | `localhost` | Cache database connection hostname |
| **MySQL Root Password (Main)** | `mysql_root_password_main` | (required) | Root access to main database |
| **MySQL Root Password (Cache)** | `mysql_root_password_cache` | (required) | Root access to cache database |
| **MySQL TLS Enabled** | `mysql_tls_enabled` | `0` (disabled) | Enable/disable TLS for MySQL connections |
| **MySQL SSL Directory** | `mysql_ssl_dir` | `/etc/mysql/ssl` | Directory for MySQL SSL certificates |
| **MySQL Server Cert Path** | `mysql_server_cert_path` | `/etc/mysql/ssl/server-cert.pem` | Server certificate file path |
| **MySQL Server Key Path** | `mysql_server_key_path` | `/etc/mysql/ssl/server-key.pem` | Server private key file path |
| **MySQL Config Path** | `mysql_config_path` | `/etc/mysql/mysql.conf.d/mysqld.cnf` | MySQL configuration file path |
| **MySQL SSL CA Path** | `ssl_ca_path` | `/etc/mysql/ssl/ca.pem` | CA certificate path (only if `mysql_tls_enabled = 1`) |
| **MySQL SSL CA Path (Cache)** | `cache_ssl_ca_path` | `/etc/mysql/ssl/ca.pem` | Cache CA certificate path (only if `mysql_tls_enabled = 1`) |

**Additional Information (not in config file, but needed for remote deployments):**
- **Deployment Box IP**: Your server's static IP - Used for MySQL root user grants (remote access only)

### File Paths

**Hardcoded Paths (not configurable):**
- None - All MySQL paths are configurable

**Configurable Paths (default values shown, can be changed in install config):**
- `mysql_ssl_dir` - Default: `/etc/mysql/ssl` - Directory for MySQL SSL certificates
- `mysql_server_cert_path` - Default: `/etc/mysql/ssl/server-cert.pem` - Server certificate file (fullchain: leaf + intermediate)
- `mysql_server_key_path` - Default: `/etc/mysql/ssl/server-key.pem` - Server private key file
- `mysql_config_path` - Default: `/etc/mysql/mysql.conf.d/mysqld.cnf` - MySQL configuration file path
- `ssl_ca_path` - Default: `/etc/mysql/ssl/ca.pem` - CA certificate bundle (root + intermediate, no leaf) - Only used if `mysql_tls_enabled = 1`
- `cache_ssl_ca_path` - Default: `/etc/mysql/ssl/ca.pem` - Cache CA certificate path - Only used if `mysql_tls_enabled = 1`

**Let's Encrypt Certificates** (see Chapter 3, only needed if `mysql_tls_enabled = 1`):
- `/etc/letsencrypt/live/db.{domain}/` - Source certificates for database subdomain
- `/etc/letsencrypt/live/cache.{domain}/` - Source certificates for cache subdomain

## Quick Start: Localhost Setup

For localhost deployments (default configuration), MySQL setup is straightforward:

1. **Install MySQL** (if not already installed):
   ```bash
   sudo apt update
   sudo apt install mysql-server
   sudo systemctl start mysql
   sudo systemctl enable mysql
   ```

2. **Set MySQL root password** (required before installation):
   ```bash
   sudo mysql_secure_installation
   ```
   Or set it directly:
   ```bash
   sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_password';"
   ```

3. **Configure install config**:
   - Set `db_host = localhost`
   - Set `cache_host = localhost`
   - Set `mysql_tls_enabled = 0` (plain text connections, no SSL required)
   - Set MySQL root passwords

4. **Verify connection**:
   ```bash
   mysql -u root -p
   ```

That's it! No SSL certificates, DNS records, or remote access configuration needed for localhost.

## MySQL Server Requirements

### Installation

MySQL must be installed and running on your database server. The installer does not install MySQL for you.

**Installation commands** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

### TLS/SSL Configuration

MySQL TLS/SSL is **optional** and controlled by the `mysql_tls_enabled` setting in your install config:

- **`mysql_tls_enabled = 0`** (default for localhost): Plain text connections, no SSL certificates required
- **`mysql_tls_enabled = 1`** (recommended for public deployments): TLS/SSL encrypted connections, SSL certificates required

**If TLS is enabled** (`mysql_tls_enabled = 1`), MySQL must be configured to use SSL certificates. The SSL setup process is covered in **Chapter 3: SSL Certificates**, but the MySQL server must be ready to accept SSL connections.

**Expected MySQL SSL configuration** (in `mysql_config_path`, default: `/etc/mysql/mysql.conf.d/mysqld.cnf`):
```ini
[mysqld]
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem
```

**Note**: These paths are configurable via `mysql_ssl_dir`, `mysql_server_cert_path`, `mysql_server_key_path`, and `mysql_config_path` in the install config.

## Database Host Configuration

### Localhost Setup (Default)

For localhost deployments (single-box setup):

- Set `db_host = localhost` in install config
- Set `cache_host = localhost` in install config
- Set `mysql_tls_enabled = 0` (plain text connections, no SSL required)
- No DNS records needed
- No remote access configuration needed
- MySQL root user already has localhost access

This is the simplest configuration and recommended for initial testing and development.

### Public Deployment (Multi-Box Setup)

For public deployments with separate database server:

- Set `db_host = db.yourdomain.tld` in install config
- Set `cache_host = cache.yourdomain.tld` in install config
- Set `mysql_tls_enabled = 1` (TLS/SSL recommended for public deployments)
- DNS A records required: `db.yourdomain.tld` and `cache.yourdomain.tld` pointing to database server IP
- SSL certificates required for `db` and `cache` subdomains (see Chapter 3)
- Remote root access must be configured (see "Advanced: Remote Access Configuration" below)

### Subsequent Installations

For additional installations on the same server:

- Reuse the same `db_host` and `cache_host` values from your first installation
- All installations share the same database server
- SSL certificates are shared (same `ssl_ca_path` and `cache_ssl_ca_path` if TLS is enabled)

## SSL Certificate Requirements

SSL certificates are **only required if `mysql_tls_enabled = 1`** in your install config.

**For localhost deployments** (`mysql_tls_enabled = 0`):
- No SSL certificates needed
- Plain text connections are used
- Suitable for local development and testing

**For public deployments** (`mysql_tls_enabled = 1`):
- SSL certificates are required for database connections
- Certificate domains: `db.{domain}` and `cache.{domain}` need Let's Encrypt certificates
- MySQL SSL directory: Certificates must be copied to `mysql_ssl_dir` (default: `/etc/mysql/ssl/`)
- CA certificate path: `ssl_ca_path` (default: `/etc/mysql/ssl/ca.pem`) is used in install config
- Certificate renewal: Certbot renewal hooks must update MySQL certificates automatically

The SSL setup process is detailed in **Chapter 3: SSL Certificates**.

**Note**: You can proceed with installation even if SSL certificates aren't set up yet (if `mysql_tls_enabled = 0`). The installer will create the config template, and database operations will work with plain text connections. For TLS-enabled deployments, database operations will fail until SSL is configured.

## Advanced: Remote Access Configuration

**Note**: This section is only relevant for multi-box deployments where the database server is separate from the deployment box. For localhost deployments, skip this section.

### Root User Permissions

The installer needs to connect to MySQL from your deployment box using the `root` user. MySQL's `root` user must be granted access from your deployment box's IP address.

**Why Remote Root Access?**

The installer runs database initialization commands (`init-db`, `add-db-users`) that require root privileges. These commands connect to MySQL from the deployment box, not from the database server itself.

### Granting Root Access

Connect to MySQL on your database server and grant root access from your deployment box IP:

```sql
-- For MySQL 8.0+
CREATE USER IF NOT EXISTS 'root'@'your.deployment.box.ip' IDENTIFIED BY 'your_mysql_root_password';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'your.deployment.box.ip' WITH GRANT OPTION;
FLUSH PRIVILEGES;

-- For MySQL 5.7 and earlier
GRANT ALL PRIVILEGES ON *.* TO 'root'@'your.deployment.box.ip' IDENTIFIED BY 'your_mysql_root_password' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

**Important**: Replace `your.deployment.box.ip` with your actual deployment server's static IP address.

### Verifying Root Access

Test the connection from your deployment box:

```bash
mysql -h db.yourdomain.tld -u root -p
```

If the connection fails with "Access denied", verify:
1. The IP address in the `GRANT` statement matches your deployment box's IP
2. The password matches your MySQL root password
3. MySQL firewall rules allow connections from that IP
4. DNS resolves `db.yourdomain.tld` to the correct IP address

## Technical Details: MySQL SSL Certificate File Mapping

Let's Encrypt certificates are copied (not symlinked) to MySQL SSL directory:

| Let's Encrypt File | MySQL SSL File      | Purpose                                       |
|--------------------|---------------------|-----------------------------------------------|
| `fullchain.pem`    | `server-cert.pem`   | Leaf + intermediate (what MySQL serves)       |
| `chain.pem`        | —                   | Intermediate (used to build ca.pem)           |
| `ISRG_Root_X1.pem` | —                   | Root CA (system CA store)                     |
| `privkey.pem`      | `server-key.pem`    | Private key                                   |
| `ca.pem`           | built from Root+R12 | Trusted CA bundle for clients/MySQL verification |

**Why Copy Instead of Symlink?**
- MySQL process needs proper file permissions
- Symlinks can cause permission issues during renewal
- Direct file access is more reliable for MySQL

**Certificate File Requirements**:
- `server-cert.pem` must be `fullchain.pem` so MySQL presents the intermediate
- `ca.pem` must be **root + intermediate only** (no leaf) - built from `ISRG_Root_X1.pem + chain.pem`
- Private key must have `600` permissions (readable/writable by owner only)
- Certificates must have `644` permissions (readable by all, writable by owner)
- All files must be owned by `mysql:mysql`

## Install Config Values

The following values from your MySQL setup go into `/root/.{project}-install.cnf`:

**For localhost deployment (default, simplest):**
```ini
[install]
# Database hosts (localhost for single-box setup)
db_host = localhost
cache_host = localhost

# MySQL root passwords (per DB host)
mysql_root_password_main = your_secure_password
mysql_root_password_cache = your_secure_password

# MySQL TLS/SSL Configuration
mysql_tls_enabled = 0  # Plain text connections, no SSL required

# MySQL SSL paths (not used if mysql_tls_enabled = 0, but must be set)
mysql_ssl_dir = /etc/mysql/ssl
mysql_server_cert_path = /etc/mysql/ssl/server-cert.pem
mysql_server_key_path = /etc/mysql/ssl/server-key.pem
mysql_config_path = /etc/mysql/mysql.conf.d/mysqld.cnf
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem
```

**For public deployment (multi-box, TLS recommended):**
```ini
[install]
# Database hosts (use your DB/cache subdomains)
db_host = db.yourdomain.tld
cache_host = cache.yourdomain.tld

# MySQL root passwords (per DB host)
mysql_root_password_main = your_secure_password
mysql_root_password_cache = your_secure_password

# MySQL TLS/SSL Configuration
mysql_tls_enabled = 1  # TLS/SSL encrypted connections

# MySQL SSL paths (all configurable)
mysql_ssl_dir = /etc/mysql/ssl
mysql_server_cert_path = /etc/mysql/ssl/server-cert.pem
mysql_server_key_path = /etc/mysql/ssl/server-key.pem
mysql_config_path = /etc/mysql/mysql.conf.d/mysqld.cnf
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem
```

## Verification

Before proceeding to installation, verify:

1. **MySQL is running**: 
   ```bash
   sudo systemctl status mysql
   ```

2. **Local connection works** (for localhost deployments):
   ```bash
   mysql -u root -p
   ```
   Or test with hostname:
   ```bash
   mysql -h localhost -u root -p
   ```

3. **Remote connection works** (for multi-box deployments only):
   ```bash
   mysql -h db.yourdomain.tld -u root -p
   ```

4. **SSL directory exists** (only if `mysql_tls_enabled = 1` and SSL is already configured):
   ```bash
   ls -la /etc/mysql/ssl/
   ```
   Or use your configured `mysql_ssl_dir` path.

5. **MySQL SSL is configured** (only if `mysql_tls_enabled = 1` and SSL is already configured):
   ```bash
   grep -E "ssl-ca|ssl-cert|ssl-key" /etc/mysql/mysql.conf.d/mysqld.cnf
   ```
   Or use your configured `mysql_config_path`.

## Next Steps

1. If SSL certificates aren't set up yet, proceed to **Chapter 3: SSL Certificates**
2. If SSL is already configured, proceed to **Chapter 5: Installation**

