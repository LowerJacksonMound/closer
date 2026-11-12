"""Put each gated repo's sandbox block in its own <repo>/.claude/settings.local.json and take the global block out
of ~/.claude/settings.json, so only a claude started inside a gated tree is sandboxed. Run from a terminal outside
Claude:
python3 ~/Desktop/CLOSER/apply_sandbox.py"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closer_gate  # noqa: E402

p = Path(os.path.expanduser("~/.claude/settings.json"))
shutil.copy(p, str(p) + ".bak")
d = json.loads(p.read_text())
if d.pop("sandbox", None) is not None:
    p.write_text(json.dumps(d, indent=2) + "\n")
    print("global sandbox block removed from", p, "(backup at", str(p) + ".bak)")

for repo, why in closer_gate.gated_repos():
    f = repo / ".claude" / "settings.local.json"
    f.parent.mkdir(exist_ok=True)
    s = json.loads(f.read_text()) if f.exists() else {}
    s["sandbox"] = closer_gate.sandbox_block([repo])
    f.write_text(json.dumps(s, indent=2) + "\n")
    ex = repo / ".git" / "info" / "exclude"  # keep the machine-specific paths out of the tree's commits
    if ex.parent.is_dir() and ".claude/settings.local.json" not in (ex.read_text().split("\n") if ex.exists() else []):
        ex.open("a").write(".claude/settings.local.json\n")
    print("sandbox block applied to", f, f"({why})")
