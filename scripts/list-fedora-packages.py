#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "prototype/distro.go")
    text = path.read_text()

    start = text.index("var fedoraLinux = &distro{")
    end = text.index("// activeDistro", start)
    lines = text[start:end].splitlines()

    packages: set[str] = set()
    mode: str | None = None
    saw_build = False
    saw_rename = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("build: []string{"):
            mode = "build"
            saw_build = True
            continue
        if stripped.startswith("rename: map[string]string{"):
            mode = "rename"
            saw_rename = True
            continue
        if mode and stripped == "},":
            mode = None
            continue

        if mode == "build":
            packages.update(re.findall(r'"([^"]+)"', line))
        elif mode == "rename":
            m = re.match(r'\s*"[^"]+"\s*:\s*"([^"]*)"', line)
            if m and m.group(1):
                packages.add(m.group(1))

    if not saw_build:
        raise SystemExit("could not find Fedora build package list")
    if not saw_rename:
        raise SystemExit("could not find Fedora rename map")

    for p in sorted(packages):
        print(p)


if __name__ == "__main__":
    main()
