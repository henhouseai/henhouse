#!/usr/bin/env bash
# Build a throwaway henhouse install for the live suite (context/testing.md TS-H06).
#
#   sudo bash tests/live/build_sandbox.sh            # from the checkout to test, as root, in a cloud sandbox
#   export HH_LIVE_PROJECT=/home/hentest/henhouse
#   python tests/harness/run_suite.py live
#
# NEVER run this on foxhouse, Lee's PC or any machine with a real install: it installs MySQL and nginx, sets the
# MySQL root password, creates a Unix user, uninstalls any earlier sandbox and writes /root/.henhouse-install.cnf.
# It refuses to run unless the machine is a sandbox it made itself or one with no henhouse on it.
#
# Tested on Ubuntu 24.04 (cloud sandbox, root, MySQL 8.0, no systemd, no IPv6).  About 25 seconds once the packages are in.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/../.." && pwd)"
OWNER="${HH_SANDBOX_OWNER:-hentest}"
PROJECT="henhouse"
DEST="/home/$OWNER/$PROJECT"
MARKER=/etc/henhouse-sandbox
ROOT_PW="Sandbox-Root-1"
APP_PW="Sandbox-Pass-1"

[ "$(id -u)" = 0 ] || { echo "run as root (sudo)"; exit 3; }
if [ ! -f "$MARKER" ] && { [ -d /srv/foxhouse ] || [ -d /foxhouse ] || [ -n "$(ls -d /srv/*/git 2>/dev/null)" ]; }; then
  echo "this machine has a henhouse install that this script did not make; refusing"; exit 3
fi
touch "$MARKER"

log() { printf '\n== %s\n' "$*"; }
hen() {  # run a henhouse command in the sandbox project; fail on an action error
  local out; out="$(cd "$DEST" && python3 hen.py "$@" 2>&1 | sed 's/\x1b\[[0-9;]*m//g')" || true
  if grep -q "Action Error" <<<"$out"; then echo "$out" | tail -40; echo "hen $* failed"; exit 1; fi
}

log "packages"
export DEBIAN_FRONTEND=noninteractive
if ! command -v mysqld >/dev/null || ! command -v nginx >/dev/null || ! command -v htpasswd >/dev/null; then
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends mysql-server-8.0 nginx apache2-utils openssh-client git ffmpeg >/dev/null
fi
python3 -m pip install -q -r "$SRC/tests/requirements.txt" mutagen pillow 2>/dev/null \
  || python3 -m pip install -q --break-system-packages -r "$SRC/tests/requirements.txt" mutagen pillow

log "shims for a box without systemd or IPv6 (sandbox only, not henhouse bugs)"
cat > /usr/local/sbin/nginx <<'SH'
#!/bin/sh
# Sandbox shim: no IPv6 here, so drop the generated `listen [::]` lines before nginx reads the config.
for f in /etc/nginx/sites-enabled/* /etc/nginx/sites-available/*; do
  [ -f "$f" ] && sed -i '/listen \[::\]/d' "$f"
done
exec /usr/sbin/nginx "$@"
SH
cat > /usr/local/bin/systemctl <<'SH'
#!/bin/sh
# Sandbox shim: no systemd here.  Handles nginx; everything else reports success.
case "$1 $2" in
  "start nginx"|"restart nginx") /usr/local/sbin/nginx -s stop 2>/dev/null; sleep 1; /usr/local/sbin/nginx ;;
  "reload nginx") /usr/local/sbin/nginx -s reload 2>/dev/null || /usr/local/sbin/nginx ;;
  "stop nginx") /usr/local/sbin/nginx -s stop ;;
  "is-active nginx") pgrep -x nginx >/dev/null && echo active || { echo inactive; exit 3; } ;;
  *) exit 0 ;;
esac
SH
chmod +x /usr/local/sbin/nginx /usr/local/bin/systemctl
rm -f /etc/nginx/sites-enabled/default
git config --system --add safe.directory '*'
grep -q "henhouse.local" /etc/hosts || echo "127.0.0.1 henhouse.local" >> /etc/hosts

log "mysql"
mkdir -p /var/run/mysqld && chown mysql:mysql /var/run/mysqld
if ! mysqladmin ping --silent 2>/dev/null; then
  (nohup mysqld --user=mysql >/var/log/mysqld-sandbox.log 2>&1 &)
  for _ in $(seq 30); do mysqladmin ping --silent 2>/dev/null && break; sleep 1; done
fi
mysql -uroot -e "SELECT 1" >/dev/null 2>&1 \
  && mysql -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY '$ROOT_PW'; FLUSH PRIVILEGES;" \
  || mysql -uroot -p"$ROOT_PW" -e "SELECT 1" >/dev/null

log "owner $OWNER"
id "$OWNER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$OWNER"
install -d -m 700 -o "$OWNER" -g "$OWNER" "/home/$OWNER/.ssh"
if [ ! -s "/home/$OWNER/.ssh/authorized_keys" ]; then   # install wants a non-empty authorized_keys
  ssh-keygen -q -t ed25519 -N "" -f "/home/$OWNER/.ssh/sandbox_key"
  cp "/home/$OWNER/.ssh/sandbox_key.pub" "/home/$OWNER/.ssh/authorized_keys"
fi
chown -R "$OWNER:$OWNER" "/home/$OWNER/.ssh"

log "tear down an earlier sandbox"
if [ -f "$DEST/hen.py" ]; then
  (cd "$DEST" && python3 hen.py flask-stop >/dev/null 2>&1; python3 hen.py maintenance-stop >/dev/null 2>&1; \
   python3 hen.py uninstall >/dev/null 2>&1) || true
fi
# Whatever uninstall left (it cannot remove tier users while their daemons run, and a failed install leaves some).
TIERS="${PROJECT}_guest ${PROJECT}_verified ${PROJECT}_admin ${PROJECT}_root"
for u in $TIERS; do pkill -u "$u" 2>/dev/null || true; done
sleep 1
for u in $TIERS; do userdel -r "$u" >/dev/null 2>&1 || true; done
for g in $(getent group | cut -d: -f1 | grep "^${PROJECT}" || true); do groupdel "$g" 2>/dev/null || true; done
rm -f "/root/hen" "/home/$OWNER/hen"
mysql -uroot -p"$ROOT_PW" -e "DROP DATABASE IF EXISTS ${PROJECT}; DROP DATABASE IF EXISTS ${PROJECT}_cache;" 2>/dev/null || true
rm -rf "$DEST" "/srv/$PROJECT" "/srv/${PROJECT}_"*

log "copy the checkout (tracked and untracked files, no .git: the cloud clone is shallow and install makes its own repo)"
mkdir -p "$DEST"
(cd "$SRC" && git ls-files -co --exclude-standard -z | tar --null -T - -cf -) | tar -x -C "$DEST"
chown -R "$OWNER:$OWNER" "$DEST"

log "install config"
CNF="/root/.${PROJECT}-install.cnf"
rm -f "$CNF"
(cd "$DEST" && python3 hen.py install >/dev/null 2>&1) || true    # first run writes the template
[ -f "$CNF" ] || { echo "install did not write $CNF"; exit 1; }
sed -i -e "s/= CHANGE_ME/= $APP_PW/" \
       -e "s/^mysql_root_password_main = .*/mysql_root_password_main = $ROOT_PW/" \
       -e "s/^mysql_root_password_cache = .*/mysql_root_password_cache = $ROOT_PW/" \
       -e "s/^domain = .*/domain = henhouse.local/" \
       -e "s#^local_allow_block = .*#local_allow_block = 127.0.0.0/8#" "$CNF"

log "install";      hen install
log "init-db";      hen init-db -root -confirm
log "add-db-users"; hen add-db-users -root
log "deploy";       hen deploy

log "ready"
echo "export HH_LIVE_PROJECT=$DEST"
echo "python tests/harness/run_suite.py live"
