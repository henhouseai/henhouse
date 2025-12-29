# Chapter 2: MySQL Server Setup

## Quick Reference

Before installing Henhouse, you need a MySQL server configured with SSL support. This quick reference lists what information you need to track and where it's used.

### Information to Track

| Component | What You Need | Where It's Used |
|-----------|---------------|-----------------|
| **Database Host** | `db.yourdomain.tld` | Install config: `db_host` |
| **Cache Host** | `cache.yourdomain.tld` | Install config: `cache_host` |
| **MySQL Root Password (Main)** | Strong password | Install config: `mysql_root_password_main` |
| **MySQL Root Password (Cache)** | Strong password (can be same) | Install config: `mysql_root_password_cache` |
| **MySQL SSL CA Path** | `/etc/mysql/ssl/ca.pem` | Install config: `ssl_ca_path` |
| **MySQL SSL CA Path (Cache)** | `/etc/mysql/ssl/ca.pem` | Install config: `cache_ssl_ca_path` |
| **Deployment Box IP** | Your server's static IP | MySQL root user grants (remote access) |
| **MySQL Config Path** | `/etc/mysql/mysql.conf.d/mysqld.cnf` | SSL certificate configuration |

### Expected File Paths

The installer expects the following MySQL-related paths:

**MySQL SSL Directory:**
- `/etc/mysql/ssl/` - Directory for MySQL SSL certificates
- `/etc/mysql/ssl/ca.pem` - CA certificate bundle (root + intermediate, no leaf)
- `/etc/mysql/ssl/server-cert.pem` - Server certificate (fullchain: leaf + intermediate)
- `/etc/mysql/ssl/server-key.pem` - Server private key

**MySQL Configuration:**
- `/etc/mysql/mysql.conf.d/mysqld.cnf` - Primary MySQL config file (Ubuntu/Debian)
- SSL settings are configured here

**Let's Encrypt Certificates** (see Chapter 3):
- `/etc/letsencrypt/live/db.{domain}/` - Source certificates for database subdomain
- `/etc/letsencrypt/live/cache.{domain}/` - Source certificates for cache subdomain

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

### SSL Configuration

MySQL must be configured to use SSL certificates. The SSL setup process is covered in **Chapter 3: SSL Certificates**, but the MySQL server must be ready to accept SSL connections.

**Expected MySQL SSL configuration** (in `/etc/mysql/mysql.conf.d/mysqld.cnf`):
```ini
[mysqld]
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem
```

## Remote Access Configuration

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

## Database Host Configuration

### First Installation

For your first Henhouse installation:
- Set `db_host = db.yourdomain.tld` in install config
- Set `cache_host = cache.yourdomain.tld` in install config
- These subdomains should point to your database server's IP address
- SSL certificates must be configured for these subdomains (see Chapter 3)

### Subsequent Installations

For additional installations on the same server:
- Reuse the same `db_host` and `cache_host` values from your first installation
- All installations share the same database server
- SSL certificates are shared (same `ssl_ca_path` and `cache_ssl_ca_path`)

## SSL Certificate Requirements

The installer expects SSL certificates to be configured for database connections. The SSL setup process is detailed in **Chapter 3: SSL Certificates**, but you need to know:

1. **Certificate domains**: `db.{domain}` and `cache.{domain}` need Let's Encrypt certificates
2. **MySQL SSL directory**: Certificates must be copied to `/etc/mysql/ssl/`
3. **CA certificate path**: `/etc/mysql/ssl/ca.pem` is used in install config
4. **Certificate renewal**: Certbot renewal hooks must update MySQL certificates automatically

**Note**: You can proceed with installation even if SSL certificates aren't set up yet. The installer will create the config template, but database operations will fail until SSL is configured. See Chapter 3 for SSL setup.

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

```ini
[install]
# Database hosts (use your DB/cache subdomains)
db_host = db.yourdomain.tld
cache_host = cache.yourdomain.tld

# MySQL root passwords (per DB host)
mysql_root_password_main = your_secure_password
mysql_root_password_cache = your_secure_password

# SSL CA paths (absolute paths)
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem
```

## Verification

Before proceeding to installation, verify:

1. **MySQL is running**: 
   ```bash
   sudo systemctl status mysql
   ```

2. **Root access from deployment box**:
   ```bash
   mysql -h db.yourdomain.tld -u root -p
   ```

3. **SSL directory exists** (if SSL is already configured):
   ```bash
   ls -la /etc/mysql/ssl/
   ```

4. **MySQL SSL is configured** (if SSL is already configured):
   ```bash
   grep -E "ssl-ca|ssl-cert|ssl-key" /etc/mysql/mysql.conf.d/mysqld.cnf
   ```

## Next Steps

1. If SSL certificates aren't set up yet, proceed to **Chapter 3: SSL Certificates**
2. If SSL is already configured, proceed to **Chapter 5: Installation**

