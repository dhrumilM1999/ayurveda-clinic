#!/usr/bin/env bash
# One-time preparation of a FRESH Ubuntu 24.04 server. Run it as root:
#     sudo bash deploy/server-setup.sh            (or:  sudo bash deploy/server-setup.sh myname)
# ASK FIRST before editing.
#
# What it does:  updates the system, makes a normal user (default name "clinic"), turns on the firewall
# (only SSH 22, web 80 and 443 are open), fail2ban (blocks password guessers), automatic security updates,
# installs Docker (official version), adds a 2 GB swap file on small servers, sets India time.
# What it does NOT do:  it never changes how you log in over SSH (that could lock you out). It only checks
# and prints advice at the end.
set -euo pipefail

[ "$(id -u)" = "0" ] || { echo "Please run with sudo:  sudo bash deploy/server-setup.sh"; exit 1; }
. /etc/os-release
if [ "${ID:-}" != "ubuntu" ]; then echo "This script is made for Ubuntu (24.04). Found: ${PRETTY_NAME:-unknown}. Stopping."; exit 1; fi
[ "${VERSION_ID%%.*}" -ge 22 ] || { echo "Ubuntu 22.04 or newer is needed."; exit 1; }

NEWUSER="${1:-clinic}"
export DEBIAN_FRONTEND=noninteractive
step() { echo; echo "=== $* ==="; }

step "1/8 Updating the system (this can take a few minutes)"
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg git ufw fail2ban unattended-upgrades apt-transport-https rclone

step "2/8 Time zone (India)"
timedatectl set-timezone Asia/Kolkata || echo "Could not set the time zone (not important)."

step "3/8 Normal user '$NEWUSER' (you will use this instead of root)"
if id "$NEWUSER" >/dev/null 2>&1; then
  echo "User $NEWUSER already exists."
else
  adduser --disabled-password --gecos "" "$NEWUSER"
  if [ -t 0 ]; then
    echo "Choose a password for $NEWUSER (needed for 'sudo'; typing is hidden):"
    until passwd "$NEWUSER"; do echo "Try again."; done
  else
    echo "WARNING: no password set for $NEWUSER (non-interactive). Set it with:  passwd $NEWUSER"
  fi
fi
usermod -aG sudo "$NEWUSER"
# Let the new user log in with the same SSH key you used for root (if any)
if [ -s /root/.ssh/authorized_keys ] && [ ! -s "/home/$NEWUSER/.ssh/authorized_keys" ]; then
  mkdir -p "/home/$NEWUSER/.ssh"
  cp /root/.ssh/authorized_keys "/home/$NEWUSER/.ssh/authorized_keys"
  chown -R "$NEWUSER:$NEWUSER" "/home/$NEWUSER/.ssh"
  chmod 700 "/home/$NEWUSER/.ssh"; chmod 600 "/home/$NEWUSER/.ssh/authorized_keys"
  echo "Copied your SSH key to $NEWUSER."
fi

step "4/8 Firewall (only ports 22, 80, 443)"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status

step "5/8 fail2ban (blocks repeated wrong SSH logins)"
cat > /etc/fail2ban/jail.local <<'JAIL'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
[sshd]
enabled = true
JAIL
systemctl enable --now fail2ban
systemctl restart fail2ban

step "6/8 Automatic security updates"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'AUTO'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
AUTO
systemctl enable --now unattended-upgrades

step "7/8 Docker (official repository)"
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Docker is already installed: $(docker --version)"
else
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi
usermod -aG docker "$NEWUSER"
# Docker logs: also cut at 10 MB for any container started outside the compose file
if [ ! -f /etc/docker/daemon.json ]; then
  printf '{\n  "log-driver": "json-file",\n  "log-opts": { "max-size": "10m", "max-file": "3" }\n}\n' > /etc/docker/daemon.json
  systemctl restart docker
fi

step "8/8 Swap file (extra memory on small servers)"
if swapon --show | grep -q .; then
  echo "Swap already exists."
else
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
  sysctl -p /etc/sysctl.d/99-swappiness.conf >/dev/null
  echo "2 GB swap created."
fi

echo
echo "================ DONE. Please read this: ================"
echo "1. Open a SECOND terminal window and test that you can log in as the new user BEFORE closing this one:"
echo "       ssh $NEWUSER@<server-ip>"
echo "2. SSH safety check (nothing was changed):"
if [ -s "/home/$NEWUSER/.ssh/authorized_keys" ]; then
  echo "   - $NEWUSER has an SSH key. Once key login works you MAY turn off password login:"
  echo "       sudo nano /etc/ssh/sshd_config.d/99-hardening.conf   containing:  PasswordAuthentication no"
  echo "                                                                         PermitRootLogin prohibit-password"
  echo "       sudo systemctl reload ssh      (keep one window open while testing!)"
else
  echo "   - WARNING: $NEWUSER has no SSH key yet, so password login must stay ON. Do NOT disable it."
  echo "     Later, add a key (see docs/GO_LIVE.md) and only then turn password login off."
fi
if sshd -T 2>/dev/null | grep -qi '^permitrootlogin yes'; then
  echo "   - Root can log in with a password. After step 1 works, forbid it:  PermitRootLogin no  in /etc/ssh/sshd_config.d/99-hardening.conf"
fi
echo "3. Next: log in as $NEWUSER, clone the code and continue with docs/GO_LIVE.md (step 'make-env')."
echo "4. Docker opens ports itself and ignores the firewall; this setup only publishes 80 and 443, which is fine."
echo "   Never add 'ports:' for the database to the compose file."
