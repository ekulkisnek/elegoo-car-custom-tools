#!/usr/bin/env bash
# Phase 3 — SSH client probe (pubkey only, matches ssh_keys_local.h / template).
# Usage: SSH_KEY=/path/to/private_key ./try_ssh_client.sh <ip_or_host>
set -euo pipefail
HOST="${1:?usage: SSH_KEY=private_key $0 <ip_or_host>}"
KEY="${SSH_KEY:?set SSH_KEY to your ed25519 private key path (same pair as EASYLIBSSH_AUTHKEY)}"
test -f "$KEY"
chmod 600 "$KEY"
exec ssh -vvv -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
  -o IdentitiesOnly=yes -o PreferredAuthentications=publickey \
  -i "$KEY" "esp32@${HOST}" "echo SSH_OK"
