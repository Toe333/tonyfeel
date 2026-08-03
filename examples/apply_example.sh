#!/usr/bin/env bash
# Apply default TonyFeel (4-bar pack @ 25%) to the demo quantized groove.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="${ROOT}/.venv/bin/tonyfeel"
if [[ ! -x "$TF" ]]; then
  echo "Install first: uv venv .venv && uv pip install --python .venv/bin/python -e ."
  exit 1
fi
"$TF" apply "$ROOT/demo/groove_quantized.mid" \
  --feel tony_bollas_mad_4bar -p 25 --seed 2007 \
  -o /tmp/groove_tonyfeel_p25.mid
echo "→ /tmp/groove_tonyfeel_p25.mid"
echo "Compare with: $ROOT/demo/groove_with_feel.mid"
