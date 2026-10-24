#!/bin/sh
# Plant: no model and no network inside the gate (KERNEL K6). The kernel (bin), the scanner, the live pack and the
# adapters import no model client and no network module, and the live pack's shell checks call no network tool.
# Fixed code decides: AST, the repo's tests, the signer's claims. Reads the real files in this tree.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
fail() { echo "PLANT no_model_in_gate: FAIL $*" >&2; exit 1; }
BAD='^[[:space:]]*(import|from)[[:space:]]+(anthropic|openai|google\.generativeai|google\.genai|litellm|langchain|transformers|requests|httpx|aiohttp|urllib\.request|urllib3|http\.client|socket|websockets)([[:space:].,]|$)'
files="$(find "$HERE/bin" "$HERE/scanner" "$HERE/pack/live" "$HERE/adapters" -type f \
  \( -name '*.py' -o -name 'gc' \) -not -path '*/__pycache__/*')"
[ -n "$files" ] || fail "no gate files found"
hits="$(echo "$files" | xargs grep -nE "$BAD" 2>/dev/null)"
[ -z "$hits" ] || fail "model or network import in the gate:
$hits"
hits="$(grep -nE '(^|[^A-Za-z_./-])(curl|wget|nc|ncat|telnet|ssh|scp)([^A-Za-z_./-]|$)' "$HERE"/pack/live/*.sh 2>/dev/null | grep -v '^[^:]*:[0-9]*:[[:space:]]*#')"
[ -z "$hits" ] || fail "network tool in a live shell check:
$hits"
n="$(echo "$files" | wc -l | tr -d ' ')"
echo "PLANT no_model_in_gate: PASS ($n gate files, 0 model or network imports)"
