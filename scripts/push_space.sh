#!/usr/bin/env bash
# Push this repo to a Hugging Face Space (requires write-scoped HF token).
# Usage:
#   hf auth login          # token with Write
#   bash scripts/push_space.sh [namespace/tonyfeel]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPACE="${1:-Toe333/tonyfeel}"

echo "Creating/updating Space: $SPACE"
hf repos create "$SPACE" --type space --space-sdk gradio --exist-ok

# Upload tracked project files (not .venv)
cd "$ROOT"
hf upload "$SPACE" . . \
  --repo-type=space \
  --exclude=".venv/*" \
  --exclude="**/__pycache__/*" \
  --exclude="**/*.egg-info/*" \
  --exclude=".git/*"

echo "Space URL: https://huggingface.co/spaces/${SPACE}"
