#!/bin/sh
# CLOSER selftest: every test under tests/, one line out. Green here is "release ready". closer_watch.py runs it first.
cd "$(dirname "$0")" || exit 1
export CLOSER_HOME="${TMPDIR:-/tmp}/closer_selftest_home"; rm -rf "$CLOSER_HOME"; mkdir -p "$CLOSER_HOME"
n=0
for t in tests/*.py; do
  n=$((n + 1)); out=$(python3 "$t" . "$(mktemp -d)" 2>&1); rc=$?
  # brittle/edges/gate/inplace exit 1 on failure; classes/shenanigans/client only print, so their failure words are read
  if [ $rc -ne 0 ] || printf '%s\n' "$out" | grep -q -E '^(BROKEN|WRITTEN|MISSING)|Traceback|^[1-9][0-9]* counterfeit'; then
    echo "SELFTEST FAIL $t"; printf '%s\n' "$out" | grep -E '^(BROKEN|WRITTEN|MISSING)|Error|counterfeit|problem' | head -6; exit 1
  fi
  echo "ok  $t: $(printf '%s\n' "$out" | grep -v '^$' | tail -1)"
done
echo "SELFTEST PASS ($n tests)"
