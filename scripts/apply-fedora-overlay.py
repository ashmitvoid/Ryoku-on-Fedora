#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

PINNED_UPSTREAM = "85cd1cbd1f9cd90f72283fbad9094772156ec4f3"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {n}")
    return text.replace(old, new, 1)


def replace_first(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n < 1:
        raise SystemExit(f"{label}: anchor not found")
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
        'func stepSysupgrade(e *engine) error {\n'
        '\td := e.d()\n',
        'func stepSysupgrade(e *engine) error {\n'
        '\td := e.d()\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\te.say("Fedora host-preserving mode: skipping automatic full-system upgrade")\n'
        '\t\treturn nil\n'
        '\t}\n',
        "skip automatic Fedora system upgrade",
    )

    s = replace_once(
        s,
        'func stepConflicts(e *engine) error {\n',
        'func stepConflicts(e *engine) error {\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\te.say("Fedora host-preserving mode: not removing host packages or disabling existing desktop daemons")\n'
        '\t\treturn nil\n'
        '\t}\n',
        "skip Fedora conflict removals",
    )

    s = replace_once(
        s,
        '\tfor _, rel := range backupMove {\n'
        '\t\tif err := saveOne(rel, true); err != nil {\n',
        '\tfor _, rel := range backupMove {\n'
        '\t\tif isFedoraHost(e.f) && rel == ".config/xdg-desktop-portal" {\n'
        '\t\t\te.say("Fedora host-preserving mode: keeping ~/.config/xdg-desktop-portal in place")\n'
        '\t\t\tcontinue\n'
        '\t\t}\n'
        '\t\tif err := saveOne(rel, true); err != nil {\n',
        "preserve Fedora portal config",
    )

    s = replace_once(
        s,
        'func stepPayload(e *engine) error {\n',
        'func stepPayload(e *engine) error {\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\treturn stepPayloadFedora(e)\n'
        '\t}\n',
        "pinned Fedora payload dispatch",
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
        '\tif isFedoraHost(e.f) {\n'
        '\t\treturn e.cmd(filepath.Join(e.payload, "ryoku", "shell"), env, "bash", script, "--no-reload")\n'
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
        'func stepFish(e *engine) error {\n',
        'func stepFish(e *engine) error {\n'
        '\tif isFedoraHost(e.f) {\n'
        '\t\te.say("Fedora host-preserving mode: keeping the current login shell")\n'
        '\t\treturn nil\n'
        '\t}\n',
        "keep Fedora login shell",
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

    sparse_old = 'append([]string{"sparse-checkout", "set"}, sparsePaths...)'
    sparse_new = 'append([]string{"sparse-checkout", "set"}, payloadSparsePathsFor(e.d())...)'
    sparse_count = s.count(sparse_old)
    if sparse_count != 2:
        raise SystemExit(f"source payload sparse paths: expected 2 anchors, found {sparse_count}")
    s = s.replace(sparse_old, sparse_new)

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
    s = replace_first(
        s,
        '\tif len(f.otherNet) > 0 {\n',
        '\tif len(f.otherNet) > 0 && !fedora {\n',
        "hide Fedora network toggle",
    )
    s = replace_first(
        s,
        '\tif len(f.rivalPkgs) > 0 {\n',
        '\tif len(f.rivalPkgs) > 0 && !fedora {\n',
        "hide Fedora rival removal",
    )
    s = replace_first(
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
    s = replace_first(
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
        'for s in "$here/../../system/hardware"/*/ryoku-* "$here/../../system/containers"/ryoku-*; do\n'
        '  [[ -f $s && -x $s ]] || continue\n'
        '  install -m755 "$s" "$bindir/${s##*/}"\n'
        'done\n',
        'if (( ! host_preserve )); then\n'
        '  for s in "$here/../../system/hardware"/*/ryoku-* "$here/../../system/containers"/ryoku-*; do\n'
        '    [[ -f $s && -x $s ]] || continue\n'
        '    install -m755 "$s" "$bindir/${s##*/}"\n'
        '  done\n'
        'else\n'
        '  say "host-preserving mode: skipped Arch hardware/container actuators"\n'
        'fi\n',
        "skip Arch hardware actuators",
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
        'install -m755 "$here/../cli/ryoku" "$bindir/ryoku"\n',
        'install -m755 "$here/../cli/ryoku" "$bindir/ryoku"\n'
        'if (( host_preserve )); then\n'
        '  mv -f "$bindir/ryoku" "$bindir/ryoku.real"\n'
        '  cat > "$bindir/ryoku" <<\'EOF\'\n'
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        'case "${1:-}" in\n'
        '  update|doctor|recovery|rollback|snapshots|track|deploy|security-key|keyboard)\n'
        '    printf \'ryoku: %s is temporarily disabled by Ryoku-on-Fedora Phase 1; Fedora still owns system management.\\n\' "${1:-command}" >&2\n'
        '    exit 2\n'
        '    ;;\n'
        'esac\n'
        'exec "$(dirname "$0")/ryoku.real" "$@"\n'
        'EOF\n'
        '  chmod 0755 "$bindir/ryoku"\n'
        '  say "installed Fedora safety wrapper around Arch system-management CLI commands"\n'
        'fi\n',
        "guard Fedora ryoku CLI",
    )

    s = replace_first(
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
        'qtver=""\n'
        'if command -v qtpaths6 >/dev/null 2>&1; then\n'
        '  qtver="$(qtpaths6 --qt-version 2>/dev/null || true)"\n'
        'elif pkg-config --exists Qt6Core 2>/dev/null; then\n'
        '  qtver="$(pkg-config --modversion Qt6Core 2>/dev/null || true)"\n'
        'elif command -v pacman >/dev/null 2>&1; then\n'
        '  qtver="$(pacman -Q qt6-base 2>/dev/null | awk \'{print $2}\')"\n'
        'fi\n',
        "portable Qt version detection",
    )

    s = replace_once(
        s,
        'if command -v makepkg >/dev/null 2>&1 && pkg-config --exists hyprland 2>/dev/null; then\n',
        'if (( ! host_preserve )) && command -v makepkg >/dev/null 2>&1 && pkg-config --exists hyprland 2>/dev/null; then\n',
        "skip Arch Hyprland plugin packaging",
    )

    s = replace_once(
        s,
        'install -Dm644 "$here/portals/hyprland-portals.conf" "$cfg/xdg-desktop-portal/hyprland-portals.conf"\n',
        'if (( ! host_preserve )); then\n'
        '  install -Dm644 "$here/portals/hyprland-portals.conf" "$cfg/xdg-desktop-portal/hyprland-portals.conf"\n'
        'else\n'
        '  say "host-preserving mode: keeping the host user portal policy untouched"\n'
        'fi\n',
        "preserve Fedora portal policy",
    )


    s = replace_once(
        s,
        'install -Dm644 "$here/../apps/spicetify/ryoku-canvas.js" "$cfg/spicetify/Extensions/ryoku-canvas.js"\n'
        'say "installed ryoku-canvas spicetify extension"\n',
        'if (( ! host_preserve )); then\n'
        '  install -Dm644 "$here/../apps/spicetify/ryoku-canvas.js" "$cfg/spicetify/Extensions/ryoku-canvas.js"\n'
        '  say "installed ryoku-canvas spicetify extension"\n'
        'else\n'
        '  say "host-preserving mode: skipped Spicetify extension injection"\n'
        'fi\n',
        "skip Fedora Spicetify injection",
    )

    s = replace_once(
        s,
        'install -Dm644 "$here/../apps/nautilus/ryoku-stash-menu.py" \\\n'
        '  "$appshare/nautilus-python/extensions/ryoku-stash-menu.py"\n'
        'say "installed nautilus stash menu -> $appshare/nautilus-python/extensions"\n',
        'if (( ! host_preserve )); then\n'
        '  install -Dm644 "$here/../apps/nautilus/ryoku-stash-menu.py" \\\n'
        '    "$appshare/nautilus-python/extensions/ryoku-stash-menu.py"\n'
        '  say "installed nautilus stash menu -> $appshare/nautilus-python/extensions"\n'
        'else\n'
        '  say "host-preserving mode: skipped Nautilus extension injection"\n'
        'fi\n',
        "skip Fedora Nautilus injection",
    )

    s = replace_once(
        s,
        'cp -a "$here/../apps/fish/config.fish" "$cfg/fish/config.fish"\n'
        'mkdir -p "$cfg/fish/conf.d"; cp -a "$here/../apps/fish/conf.d/." "$cfg/fish/conf.d/"\n'
        'mkdir -p "$cfg/ryoku-terminal"; cp -a "$here/../apps/terminal-shell/." "$cfg/ryoku-terminal/"\n'
        'mkdir -p "$cfg/bash"; cp -a "$here/../apps/bash/." "$cfg/bash/"\n'
        'mkdir -p "$cfg/zsh"; cp -a "$here/../apps/zsh/." "$cfg/zsh/"\n'
        'mkdir -p "$cfg/qt6ct"; cp -a "$here/qt6ct/qt6ct.conf" "$cfg/qt6ct/qt6ct.conf"\n',
        'mkdir -p "$cfg/ryoku-terminal"; cp -a "$here/../apps/terminal-shell/." "$cfg/ryoku-terminal/"\n'
        'if (( ! host_preserve )); then\n'
        '  cp -a "$here/../apps/fish/config.fish" "$cfg/fish/config.fish"\n'
        '  mkdir -p "$cfg/fish/conf.d"; cp -a "$here/../apps/fish/conf.d/." "$cfg/fish/conf.d/"\n'
        '  mkdir -p "$cfg/bash"; cp -a "$here/../apps/bash/." "$cfg/bash/"\n'
        '  mkdir -p "$cfg/zsh"; cp -a "$here/../apps/zsh/." "$cfg/zsh/"\n'
        '  mkdir -p "$cfg/qt6ct"; cp -a "$here/qt6ct/qt6ct.conf" "$cfg/qt6ct/qt6ct.conf"\n'
        'else\n'
        '  say "host-preserving mode: kept Fish/Bash/Zsh/Qt user configuration untouched"\n'
        'fi\n',
        "preserve Fedora shell and Qt user config",
    )

    s = replace_once(
        s,
        'mkdir -p "$cfg/gtk-3.0"; cp -a "$here/gtk-3.0/settings.ini" "$cfg/gtk-3.0/settings.ini"\n'
        'mkdir -p "$cfg/gtk-4.0"; cp -a "$here/gtk-4.0/settings.ini" "$cfg/gtk-4.0/settings.ini"\n'
        'mkdir -p "$cfg/btop"; cp -a "$here/../apps/btop/btop.conf" "$cfg/btop/btop.conf"\n'
        'mkdir -p "$cfg/fastfetch"\n'
        'cp -a "$here/../apps/fastfetch/config.jsonc" "$cfg/fastfetch/config.jsonc"\n'
        'install -m755 "$here/../apps/fastfetch/ryoku-fastfetch" "$bindir/ryoku-fastfetch"\n'
        'mkdir -p "$cfg/kitty"\n'
        'cp -a "$here/../apps/kitty/kitty.conf" "$cfg/kitty/kitty.conf"\n'
        'cp -a "$here/../apps/kitty/current-theme.conf" "$cfg/kitty/current-theme.conf"\n'
        'mkdir -p "$cfg/wireplumber"; cp -a "$here/../apps/wireplumber/." "$cfg/wireplumber/"\n',
        'install -m755 "$here/../apps/fastfetch/ryoku-fastfetch" "$bindir/ryoku-fastfetch"\n'
        'if (( ! host_preserve )); then\n'
        '  mkdir -p "$cfg/gtk-3.0"; cp -a "$here/gtk-3.0/settings.ini" "$cfg/gtk-3.0/settings.ini"\n'
        '  mkdir -p "$cfg/gtk-4.0"; cp -a "$here/gtk-4.0/settings.ini" "$cfg/gtk-4.0/settings.ini"\n'
        '  mkdir -p "$cfg/btop"; cp -a "$here/../apps/btop/btop.conf" "$cfg/btop/btop.conf"\n'
        '  mkdir -p "$cfg/fastfetch"; cp -a "$here/../apps/fastfetch/config.jsonc" "$cfg/fastfetch/config.jsonc"\n'
        '  mkdir -p "$cfg/kitty"\n'
        '  cp -a "$here/../apps/kitty/kitty.conf" "$cfg/kitty/kitty.conf"\n'
        '  cp -a "$here/../apps/kitty/current-theme.conf" "$cfg/kitty/current-theme.conf"\n'
        '  mkdir -p "$cfg/wireplumber"; cp -a "$here/../apps/wireplumber/." "$cfg/wireplumber/"\n'
        'else\n'
        '  say "host-preserving mode: kept GTK/Btop/Fastfetch/Kitty/WirePlumber user configuration untouched"\n'
        'fi\n',
        "preserve Fedora shared desktop app config",
    )

    s = replace_once(
        s,
        'systemctl --user try-restart ryogami.service 2>/dev/null || true\n',
        'if (( ! host_preserve )); then\n'
        '  systemctl --user try-restart ryogami.service 2>/dev/null || true\n'
        'fi\n',
        "avoid Fedora background daemon restart",
    )

    s = replace_once(
        s,
        'systemctl --user enable --now ryoku-ai-usage.timer 2>/dev/null || true\n',
        'if (( ! host_preserve )); then\n'
        '  systemctl --user enable --now ryoku-ai-usage.timer 2>/dev/null || true\n'
        'else\n'
        '  say "host-preserving mode: Ryoku background timers remain disabled outside the Ryoku session"\n'
        'fi\n',
        "avoid Fedora background timer enable",
    )

    s = replace_once(
        s,
        'mkdir -p "$cfg/pip"; cp -a "$here/../apps/pip/pip.conf" "$cfg/pip/pip.conf"\n',
        'if (( ! host_preserve )); then\n'
        '  mkdir -p "$cfg/pip"; cp -a "$here/../apps/pip/pip.conf" "$cfg/pip/pip.conf"\n'
        'else\n'
        '  say "host-preserving mode: kept pip user configuration untouched"\n'
        'fi\n',
        "preserve Fedora pip config",
    )

    s = replace_once(
        s,
        'if command -v sudo >/dev/null 2>&1; then\n'
        '  cmp -s "$here/../apps/mimeapps.list" /usr/share/applications/mimeapps.list ||\n'
        '    sudo install -Dm644 "$here/../apps/mimeapps.list" /usr/share/applications/mimeapps.list || true\n'
        'fi\n',
        'if (( ! host_preserve )) && command -v sudo >/dev/null 2>&1; then\n'
        '  cmp -s "$here/../apps/mimeapps.list" /usr/share/applications/mimeapps.list ||\n'
        '    sudo install -Dm644 "$here/../apps/mimeapps.list" /usr/share/applications/mimeapps.list || true\n'
        'elif (( host_preserve )); then\n'
        '  say "host-preserving mode: kept Fedora system MIME defaults untouched"\n'
        'fi\n',
        "preserve Fedora MIME defaults",
    )

    s = replace_once(
        s,
        'cp -a "$here/../apps/chromium-flags.conf" "$cfg/chromium-flags.conf"\n',
        'if (( ! host_preserve )); then\n'
        '  cp -a "$here/../apps/chromium-flags.conf" "$cfg/chromium-flags.conf"\n'
        'else\n'
        '  say "host-preserving mode: kept Chromium flags untouched"\n'
        'fi\n',
        "preserve Fedora Chromium config",
    )

    s = replace_once(
        s,
        'if [[ -f "$_iconroot/index.theme" ]] && command -v gtk-update-icon-cache >/dev/null 2>&1; then\n'
        '  gtk-update-icon-cache -qtf "$_iconroot" 2>/dev/null || true\n'
        'else\n'
        '  rm -f "$_iconroot/icon-theme.cache" 2>/dev/null || true\n'
        'fi\n',
        'if (( ! host_preserve )); then\n'
        '  if [[ -f "$_iconroot/index.theme" ]] && command -v gtk-update-icon-cache >/dev/null 2>&1; then\n'
        '    gtk-update-icon-cache -qtf "$_iconroot" 2>/dev/null || true\n'
        '  else\n'
        '    rm -f "$_iconroot/icon-theme.cache" 2>/dev/null || true\n'
        '  fi\n'
        'else\n'
        '  say "host-preserving mode: kept the host user icon cache untouched"\n'
        'fi\n',
        "preserve Fedora user icon cache",
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

    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("Fedora overlay requires a git checkout of the pinned Ryoku upstream")

    if head != PINNED_UPSTREAM:
        raise SystemExit(
            f"refusing to patch Ryoku {head}; this overlay is pinned to {PINNED_UPSTREAM}"
        )

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
