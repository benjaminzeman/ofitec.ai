#!/usr/bin/env bash
# Continuous 'y' producer. Equivalent to coreutils yes but minimal.
# Usage: ./scripts/yes.sh | <command>
# Or with a custom token: Y_TOKEN=n ./scripts/yes.sh | <command>

set -euo pipefail
TOKEN="${Y_TOKEN:-y}"
while true; do
  printf '%s\n' "$TOKEN"
done
