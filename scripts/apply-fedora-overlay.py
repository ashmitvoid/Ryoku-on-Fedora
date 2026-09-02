#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

PINNED_UPSTREAM = "85cd1cbd1f9cd90f72283fbad9094772156ec4f3"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {n}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, repl, label: str) -> str:
    rx = re.compile(pattern, re.S)
    matches = list(rx.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"{label}: expected exactly one regex match, found {len(matches)}")
    return rx.sub(repl, text, count=1)


def write(path: Path, content: str) -> None:
    path.write_text(content)


def patch_engine(path: Path) -> None:
    s = path.read_text()

    s = replace_once(
        s,
        'func defaultPlan(f *facts) *plan {\n\treturn &plan{\n',
        'func defaultPlan(f *facts) *plan {\n\tp := &plan{\n',
        "defaultPlan start",
    )
    s = replace_once(
        s,
        '\t\t// the AZERTY overrides are opt-in only; a salvaged layout already\n'
        '\t\t// covers anyone who had one configured.\n'
        '\t}\n'
        '}\n\n'
        '// azertyExclusive',
        '\t\t// the AZERTY overrides are opt-in only; a salvaged layout already\n'
        '\t\t// covers anyone who had one configured.\n'
        '\t}\n'
        '\tenforceFedoraSafePlan(f, p)\n'
        '\treturn p\n'
        '}\n\n'
        '// azertyExclusive',
        "defaultPlan return",
    )

    s = replace_once(
        s,
        '\te := &engine{f: f, p: p, dry: dry, ref: ref, payloadOverride: payloadOverride}\n'
        '\te.openLog()\n',
        '\te := &engine{f: f, p: p, dry: dry, ref: ref, payloadOverride: payloadOverride}\n'
        '\tenforceFedoraSafePlan(f, p)\n'
        '\te.openLog()\n',
        "newEngine policy",
    )

    s = replace_once(
        s,
        '\te.say("building the desktop from the payload (this takes a few minutes)")\n'
        '\treturn e.cmd(filepath.Join(e.payload, "ryoku", "shell"), nil, "bash", script)\n',
        '\te.say("building the desktop from the payload (this takes a few minutes)")\n'
        '\tenv := []string(nil)\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\tenv = []string{"RYOKU_HOST_PRESERVE=1", "RYOKU_DISTRO=fedora"}\n'
        '\t}\n'
        '\treturn e.cmd(filepath.Join(e.payload, "ryoku", "shell"), env, "bash", script)\n',
        "stepBuild host preserve",
    )

    s = replace_once(
        s,
        'func stepSession(e *engine) error {\n',
        'func stepSession(e *engine) error {\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\treturn stepSessionFedora(e)\n'
        '\t}\n',
        "stepSession Fedora dispatch",
    )

    s = replace_once(
        s,
        '\t// console + login-screen parity for an explicit AZERTY choice: the vt\n'
        '\t// keymap and SDDM\'s X11 greeter follow the desktop layout.\n'
        '\tif azerty {\n',
        '\t// console + login-screen parity for an explicit AZERTY choice stays\n'
        '\t// host-owned on Fedora M1; only the Ryoku/Hyprland layout is seeded.\n'
        '\tif azerty && !isFedoraHost(e.f) {\n',
        "Fedora keyboard host preservation",
    )

    s = replace_once(
        s,
        'func stepDoctor(e *engine) error {\n'
        '\t// doctor converges snapper (btrfs only), NVIDIA modeset, greeter perms,\n',
        'func stepDoctor(e *engine) error {\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\te.say("Fedora host-preserving mode: skipping ryoku doctor until Fedora-aware reconcilers land")\n'
        '\t\treturn nil\n'
        '\t}\n'
        '\t// doctor converges snapper (btrfs only), NVIDIA modeset, greeter perms,\n',
        "skip Arch doctor on Fedora",
    )

    s = replace_once(
        s,
        '\t_, err = os.Stat("/usr/share/wayland-sessions/hyprland.desktop")\n'
        '\tcheck(err == nil, "Hyprland wayland session registered")\n',
        '\tsessionPath := "/usr/share/wayland-sessions/hyprland.desktop"\n'
        '\tsessionLabel := "Hyprland wayland session registered"\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\tsessionPath = fedoraSessionPath\n'
        '\t\tsessionLabel = "Ryoku wayland session registered"\n'
        '\t}\n'
        '\t_, err = os.Stat(sessionPath)\n'
        '\tcheck(err == nil, sessionLabel)\n',
        "verify Fedora session",
    )

    write(path, s)


def patch_main(path: Path) -> None:
    s = path.read_text()

    s = replace_once(
        s,
        'func buildItems(f *facts, p *plan) []planItem {\n\tvar it []planItem\n',
        'func buildItems(f *facts, p *plan) []planItem {\n'
        '\tvar it []planItem\n'
        '\tfedora := isFedoraHost(f)\n',
        "buildItems Fedora flag",
    )
    s = replace_once(s, '\tif f.hasNvidia {\n', '\tif f.hasNvidia && !fedora {\n', "hide Fedora NVIDIA toggle")

    def wrap_dm(m: re.Match[str]) -> str:
        block = m.group(0)
        indented = "".join("\t" + line if line else line for line in block.splitlines(True))
        return "\tif !fedora {\n" + indented + "\t}\n"

    s = regex_once(
        s,
        r'\tif dm := f\.otherDM\(\); dm != "" \{.*?'
        r'\tit = append\(it, planItem\{"Ryoku greeter theme", gd, &p\.greeter, false\}\)\n',
        wrap_dm,
        "hide Fedora DM/greeter toggles",
    )

    s = replace_once(
        s,
        '\tif f.kbLayout == "" || f.kbLayout == "us" {\n',
        '\tif !fedora && (f.kbLayout == "" || f.kbLayout == "us") {\n',
        "hide Fedora console/login keyboard toggles",
    )
    s = replace_once(
        s,
        '\tif len(f.otherNet) > 0 {\n',
        '\tif len(f.otherNet) > 0 && !fedora {\n',
        "hide Fedora network toggle",
    )
    s = replace_once(
        s,
        '\tif len(f.rivalPkgs) > 0 {\n',
        '\tif len(f.rivalPkgs) > 0 && !fedora {\n',
        "hide Fedora rival removal",
    )
    s = replace_once(
        s,
        '\tif len(f.softUnits) > 0 {\n',
        '\tif len(f.softUnits) > 0 && !fedora {\n',
        "hide Fedora daemon disable",
    )
    s = replace_once(
        s,
        '\tit = append(it, planItem{"AUR extras", "awww (wallpaper engine), Bibata cursor, LocalSend, Voxtype", &p.aur, false})\n',
        '\tif !fedora {\n'
        '\t\tit = append(it, planItem{"AUR extras", "awww (wallpaper engine), Bibata cursor, LocalSend, Voxtype", &p.aur, false})\n'
        '\t}\n',
        "hide Fedora AUR",
    )
    s = replace_once(
        s,
        '\tif !strings.HasSuffix(f.userShell, "/fish") {\n',
        '\tif !fedora && !strings.HasSuffix(f.userShell, "/fish") {\n',
        "hide Fedora login-shell mutation",
    )

    s = replace_once(
        s,
        '\tb.WriteString(fg(cText, "Reboot to land in the Ryoku greeter and your new session.") + "\\n\\n")\n',
        '\tif isFedoraHost(m.f) {\n'
        '\t\tb.WriteString(fg(cText, "Log out, then choose Ryoku from your existing Fedora login screen.") + "\\n\\n")\n'
        '\t} else {\n'
        '\t\tb.WriteString(fg(cText, "Reboot to land in the Ryoku greeter and your new session.") + "\\n\\n")\n'
        '\t}\n',
        "Fedora completion message",
    )

    write(path, s)


def patch_deploy(path: Path) -> None:
    s = path.read_text()

    s = replace_once(
        s,
        'reload=1\n[[ "${1:-}" == "--no-reload" ]] && reload=0\n',
        'reload=1\n[[ "${1:-}" == "--no-reload" ]] && reload=0\n'
        'host_preserve="${RYOKU_HOST_PRESERVE:-0}"\n',
        "deploy host-preserve flag",
    )

    s = replace_once(
        s,
        "  printf '    install it:  sudo pacman -S --needed go\\n' >&2\n",
        "  if (( host_preserve )); then\n"
        "    printf '    install it:  sudo dnf install golang\\n' >&2\n"
        "  else\n"
        "    printf '    install it:  sudo pacman -S --needed go\\n' >&2\n"
        "  fi\n",
        "portable Go install hint",
    )

    s = replace_once(
        s,
        'for s in "$here/../../system/extras"/ryoku-*; do\n'
        '  install -m755 "$s" "$bindir/${s##*/}"\n'
        'done\n'
        '# the extras actuator (renamed from ryoku-extras-install); the ryoku-* glob\n'
        '# above no longer matches it, so install it by name.\n'
        'install -m755 "$here/../../system/extras/ryostore-install" "$bindir/ryostore-install"\n',
        'if (( ! host_preserve )); then\n'
        '  for s in "$here/../../system/extras"/ryoku-*; do\n'
        '    install -m755 "$s" "$bindir/${s##*/}"\n'
        '  done\n'
        '  # the extras actuator (renamed from ryoku-extras-install); the ryoku-* glob\n'
        '  # above no longer matches it, so install it by name.\n'
        '  install -m755 "$here/../../system/extras/ryostore-install" "$bindir/ryostore-install"\n'
        'else\n'
        '  say "host-preserving mode: skipped Arch package actuators (RyoStore system installs stay disabled)"\n'
        'fi\n',
        "skip Arch package actuators",
    )

    s = replace_once(
        s,
        'if command -v sudo >/dev/null 2>&1; then\n',
        'if (( ! host_preserve )) && command -v sudo >/dev/null 2>&1; then\n',
        "skip privileged host mutations",
    )
    s = replace_once(
        s,
        '  say "installed and applied the boot splash + Limine theme"\n'
        'fi\n\n'
        '# Record the checkout this deploy came from',
        '  say "installed and applied the boot splash + Limine theme"\n'
        'fi\n'
        'if (( host_preserve )); then\n'
        '  say "host-preserving mode: skipped privileged network helpers, system services, Plymouth and Limine changes"\n'
        'fi\n\n'
        '# Record the checkout this deploy came from',
        "host-preserve status",
    )

    s = replace_once(
        s,
        'qtver="$(pacman -Q qt6-base 2>/dev/null | awk \'{print $2}\')"\n',
        'qtver="$(pkg-config --modversion Qt6Core 2>/dev/null || pacman -Q qt6-base 2>/dev/null | awk \'{print $2}\')"\n',
        "portable Qt version detection",
    )

    write(path, s)


def patch_distro_test(path: Path) -> None:
    s = path.read_text()
    s = replace_once(
        s,
        '\t\t{"fedora", "", ""},\n',
        '\t\t{"fedora", "", "fedora"},\n',
        "Fedora distro test expectation",
    )
    write(path, s)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply-fedora-overlay.py /path/to/ryoku-arch")

    root = Path(sys.argv[1]).resolve()
    ours = Path(__file__).resolve().parents[1]

    required = [
        root / "ryoku-shell-installer" / "engine.go",
        root / "ryoku-shell-installer" / "main.go",
        root / "ryoku-shell-installer" / "distro.go",
        root / "ryoku" / "shell" / "deploy.sh",
    ]
    for p in required:
        if not p.exists():
            raise SystemExit(f"not a Ryoku checkout (missing {p})")

    # The Fedora distro table is maintained as a readable complete file in this
    # repository; the rest of the integration is deliberately small overlays.
    shutil.copy2(ours / "prototype" / "distro.go", root / "ryoku-shell-installer" / "distro.go")
    shutil.copy2(ours / "overlay" / "ryoku-shell-installer" / "fedora.go",
                 root / "ryoku-shell-installer" / "fedora.go")
    shutil.copy2(ours / "overlay" / "ryoku-shell-installer" / "fedora_test.go",
                 root / "ryoku-shell-installer" / "fedora_test.go")

    patch_engine(root / "ryoku-shell-installer" / "engine.go")
    patch_main(root / "ryoku-shell-installer" / "main.go")
    patch_deploy(root / "ryoku" / "shell" / "deploy.sh")
    patch_distro_test(root / "ryoku-shell-installer" / "distro_test.go")

    print(f"Fedora overlay applied to Ryoku baseline {PINNED_UPSTREAM}")


if __name__ == "__main__":
    main()
