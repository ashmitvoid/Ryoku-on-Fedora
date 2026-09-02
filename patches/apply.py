#!/usr/bin/env python3
"""Apply the Ryoku-on-Fedora overlay to a ryoku-arch checkout.

This intentionally uses exact, fail-closed source anchors. If upstream changes a
patched block, CI fails instead of silently applying the Fedora safety policy to
the wrong code.
"""
from pathlib import Path
import shutil
import sys


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one patch anchor, found {count}\nANCHOR:\n{old[:240]}")
    path.write_text(text.replace(old, new, 1))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply.py /path/to/ryoku-arch")
    upstream = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parents[1]

    installer = upstream / "ryoku-shell-installer"
    engine = installer / "engine.go"
    main_go = installer / "main.go"
    distro_test = installer / "distro_test.go"
    deploy = upstream / "ryoku" / "shell" / "deploy.sh"
    for p in (engine, main_go, distro_test, deploy):
        if not p.is_file():
            raise SystemExit(f"missing upstream file: {p}")

    # The distro adapter is kept as a complete file because upstream deliberately
    # centralizes package-manager knowledge there.
    shutil.copy2(root / "prototype" / "distro.go", installer / "distro.go")
    shutil.copy2(root / "overlay" / "ryoku-shell-installer" / "fedora_session.go",
                 installer / "fedora_session.go")
    shutil.copy2(root / "overlay" / "ryoku-shell-installer" / "fedora_test.go",
                 installer / "fedora_test.go")

    # Upstream's baseline test intentionally treats Fedora as unsupported.
    # Change only that expectation; all other upstream tests remain untouched.
    replace_once(
        distro_test,
        '{"fedora", "", ""},',
        '{"fedora", "", "fedora"},',
    )

    # defaultPlan: Fedora's initial port is additive. --yes must not switch the
    # DM/network/GPU stack, remove rival shells, disable user daemons, install AUR
    # extras, or change the login shell.
    replace_once(
        engine,
        'func defaultPlan(f *facts) *plan {\n\treturn &plan{',
        'func defaultPlan(f *facts) *plan {\n\tp := &plan{',
    )
    replace_once(
        engine,
        '\t\t// covers anyone who had one configured.\n\t}\n}\n\n// azertyExclusive',
        '\t\t// covers anyone who had one configured.\n\t}\n'
        '\tif f.distro != nil && f.distro.id == "fedora" {\n'
        '\t\tp.nvidia = false\n'
        '\t\tp.switchDM = false\n'
        '\t\tp.switchNet = false\n'
        '\t\tp.rivals = false\n'
        '\t\tp.softOff = false\n'
        '\t\tp.aur = false\n'
        '\t\tp.fish = false\n'
        '\t\tp.greeter = false\n'
        '\t}\n'
        '\treturn p\n'
        '}\n\n// azertyExclusive',
    )

    # The installer must not run a full Fedora upgrade as a side effect of adding
    # a desktop. Refresh metadata only; package installation remains explicit.
    replace_once(
        engine,
        'func stepSysupgrade(e *engine) error {\n\td := e.d()\n\tif d.id != "arch" {\n'
        '\t\tif err := e.sudo(d.refreshCmd...); err != nil {\n\t\t\treturn err\n\t\t}\n\t}\n'
        '\treturn e.sudo(d.updateCmd...)\n}',
        'func stepSysupgrade(e *engine) error {\n\td := e.d()\n'
        '\tif d.id == "fedora" {\n'
        '\t\te.say("Fedora host policy: refreshing DNF metadata without upgrading the whole system")\n'
        '\t\treturn e.sudo(d.refreshCmd...)\n'
        '\t}\n'
        '\tif d.id != "arch" {\n'
        '\t\tif err := e.sudo(d.refreshCmd...); err != nil {\n\t\t\treturn err\n\t\t}\n\t}\n'
        '\treturn e.sudo(d.updateCmd...)\n}',
    )

    # Source deploy gets an explicit host-preservation mode on Fedora.
    replace_once(
        engine,
        '\te.say("building the desktop from the payload (this takes a few minutes)")\n'
        '\treturn e.cmd(filepath.Join(e.payload, "ryoku", "shell"), nil, "bash", script)\n}',
        '\te.say("building the desktop from the payload (this takes a few minutes)")\n'
        '\tenv := []string(nil)\n'
        '\tif e.d().id == "fedora" {\n'
        '\t\tenv = []string{"RYOKU_PORTABLE_HOST=1"}\n'
        '\t\te.say("Fedora host policy: source deploy will skip privileged network, boot and global MIME changes")\n'
        '\t}\n'
        '\treturn e.cmd(filepath.Join(e.payload, "ryoku", "shell"), env, "bash", script)\n}',
    )

    replace_once(
        engine,
        'func stepSession(e *engine) error {\n\tif e.p.switchDM {',
        'func stepSession(e *engine) error {\n'
        '\tif e.d().id == "fedora" {\n\t\treturn stepSessionFedora(e)\n\t}\n'
        '\tif e.p.switchDM {',
    )

    # ryoku doctor currently contains pacman/Limine/Arch reconcilers. Do not let
    # the installer invoke it automatically on Fedora until doctor has a backend.
    replace_once(
        engine,
        'func stepDoctor(e *engine) error {\n\t// doctor converges snapper',
        'func stepDoctor(e *engine) error {\n'
        '\tif e.d().id == "fedora" {\n'
        '\t\te.say("Fedora host policy: skipping ryoku doctor until its package/system reconcilers are distro-aware")\n'
        '\t\treturn nil\n'
        '\t}\n'
        '\t// doctor converges snapper',
    )

    replace_once(
        engine,
        '\t_, err = os.Stat("/usr/share/wayland-sessions/hyprland.desktop")\n'
        '\tcheck(err == nil, "Hyprland wayland session registered")',
        '\tsessionFile := "/usr/share/wayland-sessions/hyprland.desktop"\n'
        '\tsessionLabel := "Hyprland wayland session registered"\n'
        '\tif e.d().id == "fedora" {\n'
        '\t\tsessionFile = "/usr/share/wayland-sessions/ryoku.desktop"\n'
        '\t\tsessionLabel = "Ryoku wayland session registered without replacing Fedora login"\n'
        '\t}\n'
        '\t_, err = os.Stat(sessionFile)\n'
        '\tcheck(err == nil, sessionLabel)',
    )

    replace_once(
        engine,
        '\t} else {\n\t\te.say(gWarn + " developer toolchain skipped: ryoku recovery needs go; install with: sudo pacman -S go")\n\t}',
        '\t} else {\n'
        '\t\thint := "sudo pacman -S go"\n'
        '\t\tif e.d().id == "fedora" {\n\t\t\thint = "sudo dnf install golang"\n\t\t}\n'
        '\t\te.say(gWarn + " developer toolchain skipped: ryoku recovery needs go; install with: " + hint)\n'
        '\t}',
    )

    # Fedora plan UI: hide switches that the safe execution path refuses.
    replace_once(
        main_go,
        'func buildItems(f *facts, p *plan) []planItem {\n\tvar it []planItem',
        'func buildItems(f *facts, p *plan) []planItem {\n\tvar it []planItem\n'
        '\tfedora := f.distro != nil && f.distro.id == "fedora"',
    )
    replace_once(main_go, '\tif f.hasNvidia {', '\tif !fedora && f.hasNvidia {')
    dm_old = '''\tif dm := f.otherDM(); dm != "" {
\t\td := "disables " + dm + " and enables SDDM (at reboot)"
\t\tif len(f.desktops) > 0 {
\t\t\td += "; " + strings.Join(f.desktops, ", ") + " stays installed and selectable at login"
\t\t}
\t\tit = append(it, planItem{"Switch login to SDDM", d, &p.switchDM, false})
\t} else if f.currentDM == "" {
\t\tit = append(it, planItem{"Enable SDDM login", "no display manager found; toggle off to keep starting Hyprland by hand", &p.switchDM, false})
\t}
\tgd := "points the SDDM login screen at the Ryoku qylock greeter"
\tif f.kdeSddmConf {
\t\tgd = "KDE's login screen settings own SDDM here; toggle on to let the Ryoku theme outrank kde_settings.conf"
\t}
\tit = append(it, planItem{"Ryoku greeter theme", gd, &p.greeter, false})'''
    dm_new = '''\tif !fedora {
\t\tif dm := f.otherDM(); dm != "" {
\t\t\td := "disables " + dm + " and enables SDDM (at reboot)"
\t\t\tif len(f.desktops) > 0 {
\t\t\t\td += "; " + strings.Join(f.desktops, ", ") + " stays installed and selectable at login"
\t\t\t}
\t\t\tit = append(it, planItem{"Switch login to SDDM", d, &p.switchDM, false})
\t\t} else if f.currentDM == "" {
\t\t\tit = append(it, planItem{"Enable SDDM login", "no display manager found; toggle off to keep starting Hyprland by hand", &p.switchDM, false})
\t\t}
\t\tgd := "points the SDDM login screen at the Ryoku qylock greeter"
\t\tif f.kdeSddmConf {
\t\t\tgd = "KDE's login screen settings own SDDM here; toggle on to let the Ryoku theme outrank kde_settings.conf"
\t\t}
\t\tit = append(it, planItem{"Ryoku greeter theme", gd, &p.greeter, false})
\t}'''
    replace_once(main_go, dm_old, dm_new)
    replace_once(
        main_go,
        '\tif f.kbLayout == "" || f.kbLayout == "us" {',
        '\tif !fedora && (f.kbLayout == "" || f.kbLayout == "us") {',
    )
    replace_once(
        main_go,
        '\tif len(f.otherNet) > 0 {',
        '\tif !fedora && len(f.otherNet) > 0 {',
    )
    replace_once(
        main_go,
        '\tit = append(it, planItem{"AUR extras", "awww (wallpaper engine), Bibata cursor, LocalSend, Voxtype", &p.aur, false})',
        '\tif !fedora {\n'
        '\t\tit = append(it, planItem{"AUR extras", "awww (wallpaper engine), Bibata cursor, LocalSend, Voxtype", &p.aur, false})\n'
        '\t}',
    )

    # Completion copy must not instruct Fedora users to reboot into a greeter we
    # intentionally did not install, nor advertise Arch-only update/doctor paths.
    replace_once(
        main_go,
        '\tb.WriteString(bold(cGreen, gCheck+" The Ryoku desktop is installed") + "\\n\\n")\n'
        '\tb.WriteString(fg(cText, "Reboot to land in the Ryoku greeter and your new session.") + "\\n\\n")\n'
        '\tb.WriteString(fg(cSub, gBullet+" updates forever:   ") + fg(cText, "ryoku update") + "\\n")\n'
        '\tb.WriteString(fg(cSub, gBullet+" health checks:     ") + fg(cText, "ryoku doctor") + "\\n")',
        '\tb.WriteString(bold(cGreen, gCheck+" The Ryoku desktop is installed") + "\\n\\n")\n'
        '\tfedora := m.eng != nil && m.eng.d().id == "fedora"\n'
        '\tif fedora {\n'
        '\t\tb.WriteString(fg(cText, "Log out, then select Ryoku from your existing Fedora login screen.") + "\\n\\n")\n'
        '\t\tb.WriteString(fg(cSub, gBullet+" system updates:     ") + fg(cText, "sudo dnf upgrade --refresh") + "\\n")\n'
        '\t\tb.WriteString(fg(cYell, gBullet+" port status:        ryoku update/doctor are intentionally disabled for Fedora M1") + "\\n")\n'
        '\t} else {\n'
        '\t\tb.WriteString(fg(cText, "Reboot to land in the Ryoku greeter and your new session.") + "\\n\\n")\n'
        '\t\tb.WriteString(fg(cSub, gBullet+" updates forever:   ") + fg(cText, "ryoku update") + "\\n")\n'
        '\t\tb.WriteString(fg(cSub, gBullet+" health checks:     ") + fg(cText, "ryoku doctor") + "\\n")\n'
        '\t}',
    )

    # Portable-host deploy mode: source compilation/user configuration is
    # allowed, privileged host integration is not.
    replace_once(
        deploy,
        'reload=1\n[[ "${1:-}" == "--no-reload" ]] && reload=0',
        'reload=1\n[[ "${1:-}" == "--no-reload" ]] && reload=0\n'
        'portable_host="${RYOKU_PORTABLE_HOST:-0}"',
    )
    text = deploy.read_text()
    gate = 'if command -v sudo >/dev/null 2>&1; then'
    count = text.count(gate)
    if count != 2:
        raise SystemExit(f"{deploy}: expected 2 privileged deploy blocks, found {count}")
    text = text.replace(gate, 'if [[ $portable_host != 1 ]] && command -v sudo >/dev/null 2>&1; then')
    deploy.write_text(text)

    replace_once(
        deploy,
        '        sudo pacman -S quickshell\n    Then run this deploy again.',
        '        sudo dnf install quickshell   # Fedora\n'
        '        sudo pacman -S quickshell    # Arch\n'
        '    Then run this deploy again.',
    )

    print("Ryoku-on-Fedora overlay applied successfully")


if __name__ == "__main__":
    main()
