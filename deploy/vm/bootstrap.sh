#!/usr/bin/env bash
# One-time setup of an Ubuntu 24.04 VM (ARM or x86) for ProtocolLedger.
# Idempotent: safe to run again. Run as the default 'ubuntu' user (uses sudo).
set -euo pipefail

if ! command -v docker >/dev/null; then
  sudo apt-get update -q
  sudo apt-get install -y -q ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -q
  sudo apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
    docker-compose-plugin
  sudo usermod -aG docker "$USER"
fi

# Small VMs (e.g. 2 GB) need swap to build the image and to absorb load peaks.
mem_kib=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
if [ "$mem_kib" -lt 3500000 ] && [ ! -f /swapfile ]; then
  sudo fallocate -l 4G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# Some images (Oracle's Ubuntu) ship iptables rules that reject everything except SSH,
# even when the cloud firewall allows 80/443. Open them on the host as well, persistently.
if sudo iptables -S INPUT | grep -q -- '-j REJECT'; then
  for port in 80 443; do
    if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
      sudo iptables -I INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT
    fi
  done
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q iptables-persistent >/dev/null
  sudo netfilter-persistent save >/dev/null
fi

if ! command -v uv >/dev/null && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/0.12.5/install.sh | sh
fi
echo "bootstrap complete"
