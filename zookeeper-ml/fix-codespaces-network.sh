#!/usr/bin/env bash
set -euo pipefail
zk_id=$(docker network inspect zookeeper-ml_default --format "{{.Id}}")
zk_bridge="br-${zk_id:0:12}"
ip link show "$zk_bridge" >/dev/null
sudo iptables-legacy -C FORWARD -i "$zk_bridge" -o "$zk_bridge" -j ACCEPT 2>/dev/null || sudo iptables-legacy -I FORWARD 1 -i "$zk_bridge" -o "$zk_bridge" -j ACCEPT
