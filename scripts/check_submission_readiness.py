#!/usr/bin/env python3
"""Fails (exit 1) if any submission-readiness gate is unmet. Run before submitting."""
import os
import re
import sys
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
checks = []


def gate(name, ok, hint=""):
    checks.append((name, bool(ok), hint))


def read(p):
    fp = os.path.join(ROOT, p)
    return open(fp).read() if os.path.exists(fp) else ""


readme = read("README.md")
gate("README has test count", re.search(r"\b\d+\s+(passing|tests)\b", readme),
     "state exact pytest count in README")
gate("SKILL.md has frontmatter", read("skill/bourse/SKILL.md").startswith("---"),
     "SKILL.md needs name/description frontmatter")
gate("Why-ONLY-sponsor present", "Why ONLY" in readme or os.path.exists(
     os.path.join(ROOT, "..", "SPONSOR_DEFENSE.md")), "add sponsor defense")
gate("no leftover TODO in README", "TODO" not in readme.split("## Layout")[0],
     "resolve TODOs above the fold")
gate(".env not committed", not os.path.exists(os.path.join(ROOT, ".env")),
     "remove .env before pushing")
# TODO gates to flip true before submit:
gate("ERC-8183 tx hash recorded", bool(re.search(r"0x[0-9a-fA-F]{64}", read("PROOF.md"))),
     "add PROOF.md with REAL BSC fund+settle tx hashes (copy PROOF.template.md)")
gate("demo video linked", "youtu" in readme or "loom" in readme or "vimeo" in readme,
     "link the <=3min demo in README")

try:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    gate("pytest passes", r.returncode == 0, r.stdout[-200:])
except Exception as e:
    gate("pytest passes", False, str(e))

print("\nSubmission readiness:")
fail = 0
for name, ok, hint in checks:
    print(f"  [{'x' if ok else ' '}] {name}" + ("" if ok else f"   -> {hint}"))
    fail += not ok
print(f"\n{len(checks)-fail}/{len(checks)} gates passed")
sys.exit(1 if fail else 0)
