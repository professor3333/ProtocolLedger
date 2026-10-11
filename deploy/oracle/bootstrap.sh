#!/usr/bin/env bash
# One-time setup of an Oracle Cloud Always Free Ubuntu 24.04 (ARM) VM for ProtocolLedger.
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

# Oracle's Ubuntu images ship iptables rules that reject everything except SSH, even when
# the cloud security list allows 80/443. Open them on the host as well, persistently.
for port in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 6 -p tcp --dport "$port" -m state --state NEW -j ACCEPT
  fi
done
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q iptables-persistent >/dev/null
sudo netfilter-persistent save >/dev/null

if ! command -v uv >/dev/null && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/0.12.5/install.sh | sh
fi
echo "bootstrap complete"
