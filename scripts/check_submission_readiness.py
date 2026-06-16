#!/usr/bin/env python3
"""Submission-readiness gate. Exits 1 if any REQUIRED Track-2 gate is unmet.

Required gates = what makes the Track-2 submission valid + credible.
Optional gates = special-prize extras (on-chain proof, recorded video) that
strengthen the discretionary score but are not needed for a valid Track-2 entry
(Track 2 needs a Skill + backtestable spec + repo with clear setup instructions).
"""
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read(p):
    fp = os.path.join(ROOT, p)
    return open(fp).read() if os.path.exists(fp) else ""


def is_tracked(path):
    r = subprocess.run(["git", "ls-files", "--error-unmatch", path],
                       cwd=ROOT, capture_output=True)
    return r.returncode == 0


def pytest_count():
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        m = re.search(r"(\d+)\s+tests?\s+collected", r.stdout)
        return int(m.group(1)) if m else r.stdout.count("::")
    except Exception:
        return 0


def pytest_passes():
    try:
        return subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT,
                              capture_output=True, text=True, timeout=180).returncode == 0
    except Exception:
        return False


def build_gates():
    readme = read("README.md")
    demo = read("DEMO.md")
    skill = read("skill/bourse/SKILL.md")
    required, optional = [], []

    def req(name, ok, hint=""):
        required.append((name, bool(ok), hint))

    def opt(name, ok, hint=""):
        optional.append((name, bool(ok), hint))

    # ---- REQUIRED (Track-2 validity + credibility) ----------------------- #
    req("SKILL.md has frontmatter", skill.startswith("---"),
        "SKILL.md needs name/description frontmatter")
    req("Why-ONLY sponsor defense present", "Why ONLY" in readme,
        "add a 'Why ONLY this stack' section to README")
    req("no leftover TODO above the fold", "TODO" not in readme.split("## 📁")[0],
        "resolve TODOs above the Layout section")
    req(".env not committed", not is_tracked(".env"),
        "remove .env from git tracking before pushing")
    req("README images tracked (not gitignored)",
        is_tracked("docs/readme.png") and is_tracked("docs/readme-hero.png"),
        "git add docs/*.png so the README renders on GitHub")
    req("clear setup instructions (DEMO.md run steps)",
        "scripts/signal.py" in demo and "pip install" in demo,
        "DEMO.md must show runnable steps")

    # Truthful test count: a "<N> passing/tests" claim must not exceed what
    # pytest actually collects (this caught the old '100+ but 15' mismatch).
    claim = re.search(r"(\d+)\s+(?:passing|tests)\b", readme)
    collected = pytest_count()
    req("README test count is truthful",
        bool(claim) and collected >= int(claim.group(1)) > 0,
        f"README claims {claim.group(1) if claim else '?'}; pytest collects {collected}")

    req("pytest passes", pytest_passes(), "tests are failing")

    # ---- OPTIONAL (special-prize extras) --------------------------------- #
    real_video = bool(re.search(r"(youtu\.be/|youtube\.com/|loom\.com/|vimeo\.com/)\S+",
                                readme)) and not re.search(
        r"your-video|REPLACE_ME|example\.com", readme)
    opt("recorded demo video linked", real_video,
        "record the <=3min video and link it (setup instructions already satisfy Track 2)")
    opt("ERC-8183 on-chain proof recorded",
        bool(re.search(r"0x[0-9a-fA-F]{64}", read("PROOF.md"))),
        "run identity.py -> buyer.py -> settle.py, paste tx hashes into PROOF.md")

    return required, optional


def show(title, bucket):
    print(f"\n{title}:")
    for name, ok, hint in bucket:
        print(f"  [{'x' if ok else ' '}] {name}" + ("" if ok else f"   -> {hint}"))
    return sum(not ok for _, ok, _ in bucket)


def main():
    required, optional = build_gates()
    req_fail = show("REQUIRED (Track-2 validity)", required)
    show("OPTIONAL (special-prize extras)", optional)
    print(f"\nRequired: {len(required) - req_fail}/{len(required)} passed", end="")
    print("  ✅ submission-ready" if not req_fail else "  ❌ not ready")
    sys.exit(1 if req_fail else 0)


if __name__ == "__main__":
    main()
