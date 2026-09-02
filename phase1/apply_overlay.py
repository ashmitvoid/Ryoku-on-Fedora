#!/usr/bin/env python3
"""Apply the Ryoku-on-Fedora Phase 1 overlay to a clean ryoku-arch checkout.

The transformations are deliberately anchored and fail closed. If upstream moves
one of the touched blocks, CI fails instead of silently producing a partially
safe installer.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


def wrap_between_once(path: Path, start: str, end: str, before: str, after: str) -> None:
    text = path.read_text()
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"{path}: start anchor missing: {start!r}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"{path}: end anchor missing: {end!r}")
    if text.find(start, i + 1) >= 0:
        raise SystemExit(f"{path}: start anchor is not unique: {start!r}")
    block = text[i:j]
    path.write_text(text[:i] + before + block + after + text[j:])


def patch_engine(path: Path) -> None:
    replace_once(
        path,
        '''var sparsePaths = []string{
	"ryoku/lockscreen", "ryoku/assets", "ryoku/apps",
	"system/hardware/drivers", "system/hardware/input",
	"system/packages", "release/packages/ryoku-keyring",
}''',
        '''var sparsePaths = []string{
	// Source-based distros build these components from the payload. Keep this
	// list explicit so a partial cache cannot appear valid while missing a Go or
	// QML module needed by deploy.sh.
	"ryoku/shell", "ryoku/hub", "ryoku/rashin", "ryoku/cli", "ryoku/ui",
	"ryoku/hyprland", "ryoku/lockscreen", "ryoku/assets", "ryoku/apps",
	"system/hardware", "system/containers", "system/extras", "system/packages",
	"release/packages",
}''',
    )

    replace_once(
        path,
        '''func stepSysupgrade(e *engine) error {
	d := e.d()
	if d.id != "arch" {''',
        '''func stepSysupgrade(e *engine) error {
	d := e.d()
	if d.id == "fedora" {
		e.say("Fedora host preserved: skipping an automatic full-system upgrade")
		return nil
	}
	if d.id != "arch" {''',
    )

    replace_once(
        path,
        '''	for _, rel := range backupMove {
		if err := saveOne(rel, true); err != nil {''',
        '''	for _, rel := range backupMove {
		// A user-level portal policy can affect every desktop session. Fedora M1
		// is additive, so leave an existing portal tree in place and only add a
		// Ryoku-specific portal file later when the Hyprland backend is present.
		if isFedoraFacts(e.f) && rel == ".config/xdg-desktop-portal" {
			e.say("Fedora host preserved: keeping ~/.config/xdg-desktop-portal in place")
			continue
		}
		if err := saveOne(rel, true); err != nil {''',
    )

    replace_once(
        path,
        '''func stepConflicts(e *engine) error {
	// units first, while their unit files still exist.''',
        '''func stepConflicts(e *engine) error {
	if isFedoraFacts(e.f) {
		e.say("Fedora host preserved: not removing packages or disabling existing desktop daemons")
		return nil
	}
	// units first, while their unit files still exist.''',
    )

    replace_once(
        path,
        '''func stepBuild(e *engine) error {
	script := filepath.Join(e.payload, "ryoku", "shell", "deploy.sh")
	if e.dry {
		e.say("DRYRUN: would run " + script)
		return nil
	}
	if _, err := os.Stat(script); err != nil {
		return fmt.Errorf("payload is missing ryoku/shell/deploy.sh")
	}
	e.say("building the desktop from the payload (this takes a few minutes)")
	return e.cmd(filepath.Join(e.payload, "ryoku", "shell"), nil, "bash", script)
}''',
        '''func stepBuild(e *engine) error {
	script := filepath.Join(e.payload, "ryoku", "shell", "deploy.sh")
	if e.dry {
		if isFedoraFacts(e.f) {
			e.say("DRYRUN: would run " + script + " with RYOKU_HOST_PRESERVE=1")
		} else {
			e.say("DRYRUN: would run " + script)
		}
		return nil
	}
	if _, err := os.Stat(script); err != nil {
		return fmt.Errorf("payload is missing ryoku/shell/deploy.sh")
	}
	e.say("building the desktop from the payload (this takes a few minutes)")
	if isFedoraFacts(e.f) {
		return e.cmd(filepath.Join(e.payload, "ryoku", "shell"),
			[]string{"RYOKU_HOST_PRESERVE=1"}, "bash", script, "--no-reload")
	}
	return e.cmd(filepath.Join(e.payload, "ryoku", "shell"), nil, "bash", script)
}''',
    )

    replace_once(
        path,
        '''func stepSession(e *engine) error {
	if e.p.switchDM {''',
        '''func stepSession(e *engine) error {
	if isFedoraFacts(e.f) {
		return stepSessionFedora(e)
	}
	if e.p.switchDM {''',
    )

    replace_once(
        path,
        '''	azerty := e.p.azertyFR || e.p.azertyBE''',
        '''	azerty := !isFedoraFacts(e.f) && (e.p.azertyFR || e.p.azertyBE)''',
    )

    replace_once(
        path,
        '''func stepFish(e *engine) error {
	if !e.p.fish {''',
        '''func stepFish(e *engine) error {
	if isFedoraFacts(e.f) {
		e.say("Fedora host preserved: keeping your current login shell")
		return nil
	}
	if !e.p.fish {''',
    )

    replace_once(
        path,
        '''func stepDoctor(e *engine) error {
	// doctor converges snapper (btrfs only), NVIDIA modeset, greeter perms,''',
        '''func stepDoctor(e *engine) error {
	if isFedoraFacts(e.f) {
		e.say("Fedora Phase 1: ryoku doctor is guarded until its reconcilers have DNF/RPM backends")
		return nil
	}
	// doctor converges snapper (btrfs only), NVIDIA modeset, greeter perms,''',
    )

    replace_once(
        path,
        '''	_, err = os.Stat("/usr/share/wayland-sessions/hyprland.desktop")
	check(err == nil, "Hyprland wayland session registered")''',
        '''	sessionPath := "/usr/share/wayland-sessions/hyprland.desktop"
	sessionLabel := "Hyprland wayland session registered"
	if isFedoraFacts(e.f) {
		sessionPath = fedoraSessionPath
		sessionLabel = "Ryoku wayland session registered alongside the existing desktop"
	}
	_, err = os.Stat(sessionPath)
	check(err == nil, sessionLabel)''',
    )

    replace_once(
        path,
        '''	if !has("awww") {
		e.say(gWarn + " awww missing (AUR): static wallpapers will not set until it installs (ryoku doctor retries it)")
	}''',
        '''	if !has("awww") {
		if isFedoraFacts(e.f) {
			e.say(gWarn + " awww is not in the Fedora Phase 1 package set yet; wallpaper animation is temporarily unavailable")
		} else {
			e.say(gWarn + " awww missing (AUR): static wallpapers will not set until it installs (ryoku doctor retries it)")
		}
	}''',
    )

    replace_once(
        path,
        '''	} else {
		e.say(gWarn + " developer toolchain skipped: ryoku recovery needs go; install with: sudo pacman -S go")
	}''',
        '''	} else {
		if isFedoraFacts(e.f) {
			e.say(gWarn + " optional developer toolchain skipped; install Go later with: sudo dnf install golang")
		} else {
			e.say(gWarn + " developer toolchain skipped: ryoku recovery needs go; install with: sudo pacman -S go")
		}
	}''',
    )


def patch_main(path: Path) -> None:
    replace_once(
        path,
        '''func defaultPlan(f *facts) *plan {
	return &plan{''',
        '''func defaultPlan(f *facts) *plan {
	if isFedoraFacts(f) {
		return fedoraDefaultPlan(f)
	}
	return &plan{''',
    )

    replace_once(
        path,
        '''func buildItems(f *facts, p *plan) []planItem {
	var it []planItem''',
        '''func buildItems(f *facts, p *plan) []planItem {
	if isFedoraFacts(f) {
		return buildFedoraItems(f, p)
	}
	var it []planItem''',
    )

    replace_once(
        path,
        '''	var b strings.Builder
	b.WriteString(bold(cGreen, gCheck+" The Ryoku desktop is installed") + "\n\n")
	b.WriteString(fg(cText, "Reboot to land in the Ryoku greeter and your new session.") + "\n\n")
	b.WriteString(fg(cSub, gBullet+" updates forever:   ") + fg(cText, "ryoku update") + "\n")
	b.WriteString(fg(cSub, gBullet+" health checks:     ") + fg(cText, "ryoku doctor") + "\n")''',
        '''	var b strings.Builder
	if isFedoraFacts(m.f) {
		b.WriteString(bold(cGreen, gCheck+" The Ryoku desktop is installed on Fedora") + "\n\n")
		b.WriteString(fg(cText, "Log out and select Ryoku in your existing login manager.") + "\n\n")
		b.WriteString(fg(cSub, gBullet+" Fedora updates:      ") + fg(cText, "sudo dnf upgrade --refresh") + "\n")
		b.WriteString(fg(cSub, gBullet+" Phase 1 guardrails:  ") + fg(cText, "ryoku update/doctor/recovery remain disabled") + "\n")
	} else {
		b.WriteString(bold(cGreen, gCheck+" The Ryoku desktop is installed") + "\n\n")
		b.WriteString(fg(cText, "Reboot to land in the Ryoku greeter and your new session.") + "\n\n")
		b.WriteString(fg(cSub, gBullet+" updates forever:   ") + fg(cText, "ryoku update") + "\n")
		b.WriteString(fg(cSub, gBullet+" health checks:     ") + fg(cText, "ryoku doctor") + "\n")
	}''',
    )


def patch_deploy(path: Path) -> None:
    replace_once(
        path,
        '''bindir="$HOME/.local/bin"
say() { printf '  %s\\n' "$*"; }''',
        '''bindir="$HOME/.local/bin"
host_preserve="${RYOKU_HOST_PRESERVE:-0}"
say() { printf '  %s\\n' "$*"; }
if [[ $host_preserve == 1 ]]; then
  say "host-preserving source deploy: system boot, PAM, package and network policy stay with the host distro"
fi''',
    )

    # Guard the hardware/package actuators copied into ~/.local/bin. Their
    # current implementations assume pacman, lib32 and Ryoku's Arch policies.
    start = '# every system helper the package ships to /usr/bin, by the same globs, so a new\n'
    end = '# AI-usage collectors: refresh ~/.cache/{claude,codex,opencode}-usage.json for\n'
    wrap_between_once(
        path,
        start,
        end,
        'if [[ $host_preserve != 1 ]]; then\n',
        'else\n  say "host-preserving mode: skipped Arch hardware/package actuators"\nfi\n',
    )

    replace_once(
        path,
        '''install -m755 "$here/../cli/ryoku" "$bindir/ryoku"''',
        '''install -m755 "$here/../cli/ryoku" "$bindir/ryoku"
if [[ $host_preserve == 1 ]]; then
  # Keep the desktop/user commands available while fail-closing the commands
  # whose current implementations orchestrate pacman/yay/snapper/PAM.
  mv -f "$bindir/ryoku" "$bindir/ryoku.real"
  cat > "$bindir/ryoku" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  update|doctor|recovery|rollback|snapshots|track|deploy|security-key|keyboard)
    printf 'ryoku: %s is temporarily disabled by Ryoku-on-Fedora Phase 1; Fedora still owns system management.\\n' "${1:-command}" >&2
    exit 2
    ;;
esac
exec "$(dirname "$0")/ryoku.real" "$@"
EOF
  chmod 0755 "$bindir/ryoku"
  say "installed Fedora safety wrapper around system-management CLI commands"
fi''',
    )

    replace_once(
        path,
        '''if command -v sudo >/dev/null 2>&1; then
  netdir="$here/../../system/hardware/network"''',
        '''if [[ $host_preserve != 1 ]] && command -v sudo >/dev/null 2>&1; then
  netdir="$here/../../system/hardware/network"''',
    )

    replace_once(
        path,
        '''qtver="$(pacman -Q qt6-base 2>/dev/null | awk '{print $2}')"''',
        '''qtver=""
if command -v qtpaths6 >/dev/null 2>&1; then
  qtver="$(qtpaths6 --qt-version 2>/dev/null || true)"
elif pkg-config --exists Qt6Core 2>/dev/null; then
  qtver="$(pkg-config --modversion Qt6Core 2>/dev/null || true)"
elif command -v pacman >/dev/null 2>&1; then
  qtver="$(pacman -Q qt6-base 2>/dev/null | awk '{print $2}')"
fi''',
    )

    replace_once(
        path,
        '''if command -v makepkg >/dev/null 2>&1 && pkg-config --exists hyprland 2>/dev/null; then''',
        '''if [[ $host_preserve != 1 ]] && command -v makepkg >/dev/null 2>&1 && pkg-config --exists hyprland 2>/dev/null; then''',
    )

    replace_once(
        path,
        '''install -Dm644 "$here/portals/hyprland-portals.conf" "$cfg/xdg-desktop-portal/hyprland-portals.conf"''',
        '''if [[ $host_preserve != 1 ]] || (command -v rpm >/dev/null 2>&1 && rpm -q xdg-desktop-portal-hyprland >/dev/null 2>&1); then
  install -Dm644 "$here/portals/hyprland-portals.conf" "$cfg/xdg-desktop-portal/hyprland-portals.conf"
else
  say "host-preserving mode: xdg-desktop-portal-hyprland is absent, keeping the host portal policy untouched"
fi''',
    )

    replace_once(
        path,
        '''say "installed Ryoku CLI and hardware helpers"''',
        '''say "installed Ryoku CLI"''',
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("upstream", type=Path, help="clean ryoku-arch checkout")
    ap.add_argument("--overlay-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()

    upstream = args.upstream.resolve()
    overlay_root = args.overlay_root.resolve()

    installer = upstream / "ryoku-shell-installer"
    shutil.copy2(overlay_root / "prototype/distro.go", installer / "distro.go")
    shutil.copy2(
        overlay_root / "phase1/overlay/ryoku-shell-installer/fedora.go",
        installer / "fedora.go",
    )

    patch_engine(installer / "engine.go")
    patch_main(installer / "main.go")
    patch_deploy(upstream / "ryoku/shell/deploy.sh")

    print("Ryoku-on-Fedora Phase 1 overlay applied successfully")


if __name__ == "__main__":
    main()
