#!/usr/bin/env python3
"""Print the Fedora packages the current Ryoku adapter intends to install.

The Fedora mapper is strict/fail-closed. This parser is intentionally small and
validates only the declarative Fedora distro block in prototype/distro.go so CI
can ask a real Fedora repository whether every non-empty target exists.
"""
from pathlib import Path
import re
import sys

path = Path(__file__).resolve().parents[1] / "prototype" / "distro.go"
text = path.read_text()
marker = "var fedoraLinux = &distro{"
if marker not in text:
    raise SystemExit("fedoraLinux block not found")

block = text.split(marker, 1)[1].split("// activeDistro", 1)[0]

build_match = re.search(r"\bbuild:\s*\[\]string\{(.*?)\n\s*\},\n\s*rename:", block, re.S)
if not build_match:
    raise SystemExit("Fedora build package list not found")
build = re.findall(r'"([^"]+)"', build_match.group(1))

rename_match = re.search(r"\brename:\s*map\[string\]string\{(.*?)\n\s*\},\n\}", block, re.S)
if not rename_match:
    raise SystemExit("Fedora rename map not found")
pairs = re.findall(r'^\s*"([^"]+)"\s*:\s*"([^"]*)",', rename_match.group(1), re.M)

targets = set(build)
for _, target in pairs:
    if target:
        targets.add(target)

for pkg in sorted(targets, key=str.lower):
    print(pkg)

print(f"# {len(targets)} Fedora packages", file=sys.stderr)
