#!/bin/sh
# Plant: C1 is clean on honest code in a src layout: claims with setup, a result, a raises and a true predicate all hold on pkg.mod; the land proceeds and C1 counts them.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(mktemp -d)" || exit 1
T="$(cd "$T" && pwd -P)"
trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
fail() { echo "PLANT c1_held: FAIL $*" >&2; exit 1; }
R="$T/repo"; ST="$T/state"
gc() { python3 "$HERE/bin/gc" --repo "$R" --state "$ST" "$@"; }
mkdir -p "$R"
echo notes > "$R/README.txt"
mkdir -p "$R/src/pkg"
printf 'def f():\n    return 1\n' > "$R/src/pkg/mod.py"; : > "$R/src/pkg/__init__.py"
CL="$T/claims.json"; printf '%s' '[{"name":"pkg.mod.Counter.add","setup":["c = Counter()","c.add(2)"],"call":"c.add(3)","expect":{"result":5}},{"name":"pkg.mod.Counter.add","setup":["c = Counter()"],"call":"c.add(\"x\")","expect":{"raises":"TypeError"}},{"name":"pkg.mod.Counter.add","setup":["c = Counter()","c.add(1)"],"call":"c.add(1)","expect":{"true":"c.total == 2"}}]' > "$CL"
gc init >/dev/null 2>&1 && gc scan >/dev/null 2>&1 || fail "init/scan"
gc ticket --write src/pkg/mod.py --id T1 --claims "$CL" >/dev/null 2>&1 || fail "mint T1"
mkdir -p "$ST/payload/T1/src/pkg"
cat > "$ST/payload/T1/src/pkg/mod.py" <<'PYX'
def f():
    return 1


class Counter:
    def __init__(self):
        self.total = 0

    def add(self, n):
        if not isinstance(n, int):
            raise TypeError(n)
        self.total += n
        return self.total
PYX
gc land --ticket T1 > "$T/land" 2>&1 || fail "honest src-layout ticket did not land: $(tail -4 "$T/land")"
grep -q "^C1 pass: 3 claim(s) held on 1 function(s)" "$T/land" || fail "C1 pass line wrong: $(grep C1 "$T/land")"
echo "PLANT c1_held: PASS"
