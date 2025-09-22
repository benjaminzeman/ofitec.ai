#!/usr/bin/env bash
# Safer auto-yes wrapper: only allows commands in a whitelist.
# Usage: ./scripts/whitelisted_yes.sh npm install
set -euo pipefail
ALLOW=(npm yarn pnpm pip docker terraform)
if [ $# -eq 0 ]; then
  echo "Usage: $0 <command> [args...]" >&2
  exit 1
fi
cmd=$1; shift || true
if [[ ! " ${ALLOW[*]} " =~ " ${cmd} " ]]; then
  echo "[whitelisted_yes] Blocked command: $cmd" >&2
  exit 2
fi
# shellcheck disable=SC2068
yes | $cmd $@
