#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
engine = (root / "ryoku-shell-installer/engine.go").read_text()
distro = (root / "ryoku-shell-installer/distro.go").read_text()
fedora = (root / "ryoku-shell-installer/fedora.go").read_text()
main = (root / "ryoku-shell-installer/main.go").read_text()
deploy = (root / "ryoku/shell/deploy.sh").read_text()

checks = {
    "Fedora distro detected": 'id:           "fedora"' in distro and 'return fedoraLinux' in distro,
    "Fedora package map fails closed": "strictRename: true" in distro,
    "SDDM not installed by Fedora map": '"sddm":                   ""' in distro,
    "Fedora defaults are host-preserving": "return fedoraDefaultPlan(f)" in main,
    "Fedora TUI hides unsafe conversion toggles": "return buildFedoraItems(f, p)" in main,
    "Fedora skips automatic host upgrade": "skipping an automatic full-system upgrade" in engine,
    "Fedora skips package/daemon conflict removal": "not removing packages or disabling existing desktop daemons" in engine,
    "Fedora source build exports host-preserve mode": '[]string{"RYOKU_HOST_PRESERVE=1"}' in engine,
    "Fedora session bypasses SDDM path": "return stepSessionFedora(e)" in engine,
    "Fedora doctor is guarded": "ryoku doctor is guarded" in engine,
    "Fedora keeps login shell": "keeping your current login shell" in engine,
    "Fedora session has a distinct marker": "X-Ryoku-Fedora=1" in fedora,
    "Fedora session preserves PAM/network/SELinux": "existing display manager, PAM, SELinux and network policy were not changed" in fedora,
    "Deploy has host-preserving switch": 'host_preserve="${RYOKU_HOST_PRESERVE:-0}"' in deploy,
    "Deploy blocks privileged network/boot path": 'if [[ $host_preserve != 1 ]] && command -v sudo' in deploy,
    "Deploy blocks Arch compositor plugin build": 'if [[ $host_preserve != 1 ]] && command -v makepkg' in deploy,
    "Deploy uses distro-neutral Qt probe": "qtpaths6 --qt-version" in deploy and "pkg-config --modversion Qt6Core" in deploy,
    "Fedora CLI blocks Arch system-management commands": "update|doctor|recovery|rollback|snapshots|track|deploy|security-key|keyboard" in deploy,
    "Portal policy is not replaced without Hyprland backend": "keeping the host portal policy untouched" in deploy,
    "Source payload includes shell": '"ryoku/shell"' in engine,
    "Source payload includes hub/cli/ui": all(x in engine for x in ('"ryoku/hub"', '"ryoku/cli"', '"ryoku/ui"')),
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"[{'OK' if ok else 'FAIL'}] {name}")

if failed:
    print("\nFailed safety assertions:")
    for name in failed:
        print(f" - {name}")
    raise SystemExit(1)

print(f"\n{len(checks)} Phase 1 safety assertions passed.")
