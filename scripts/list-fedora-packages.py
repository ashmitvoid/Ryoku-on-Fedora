#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "prototype/distro.go")
    text = path.read_text()

    start = text.index("var fedoraLinux = &distro{")
    end = text.index("\n}\n\n// activeDistro", start)
    block = text[start:end]

    packages: set[str] = set()

    build_match = re.search(r'build:\s*\[\]string\{(.*?)\n\s*\},', block, re.S)
    if not build_match:
        raise SystemExit("could not find Fedora build package list")
    packages.update(re.findall(r'"([^"]+)"', build_match.group(1)))

    rename_match = re.search(r'rename:\s*map\[string\]string\{(.*)\n\s*\},\n$', block, re.S)
    if not rename_match:
        raise SystemExit("could not find Fedora rename map")
    for line in rename_match.group(1).splitlines():
        m = re.match(r'\s*"[^"]+"\s*:\s*"([^"]*)"', line)
        if m and m.group(1):
            packages.add(m.group(1))

    for p in sorted(packages):
        print(p)


if __name__ == "__main__":
    main()
