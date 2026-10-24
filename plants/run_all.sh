#!/bin/sh
# Every plant in this dir, each against the real kernel (gc selftest runs this). Exit 1 if any fails.
set -u
DIR="$(cd "$(dirname "$0")" && pwd -P)"
# Exit 77 from a plant = NOT MEASURED: the interpreter it needs is not on this machine and no GC_PLANT_* names one.
# Counted and printed; not a failure. Any other non-zero exit is a FAIL (2026-10-23, release rung 0).
rc=0; pass=0; fail=0; nm=0
for p in "$DIR"/*.sh; do
  [ "$(basename "$p")" = "run_all.sh" ] && continue
  if sh "$p"; then pass=$((pass+1)); else
    case $? in 77) nm=$((nm+1));; *) fail=$((fail+1)); rc=1;; esac
  fi
done
echo "plants: $([ "$rc" -eq 0 ] && echo PASS || echo FAIL) — $pass PASS / $fail FAIL / $nm NOT MEASURED"
exit $rc
