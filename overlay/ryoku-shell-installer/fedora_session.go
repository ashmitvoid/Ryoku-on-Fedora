package main

import (
	"fmt"
	"path/filepath"
)

// fedoraSessionDesktop is deliberately a separate Ryoku session instead of
// replacing Fedora's existing desktop/session registration. Hyprland 0.55+
// discovers ~/.config/hypr/hyprland.lua directly, which is Ryoku's config entry.
const fedoraSessionDesktop = `[Desktop Entry]
Name=Ryoku
Comment=Ryoku desktop session
Exec=Hyprland
TryExec=Hyprland
Type=Application
DesktopNames=Hyprland;Ryoku
X-GDM-SessionRegisters=true
`

// stepSessionFedora is the M1 host-preserving session policy.
//
// Fedora remains responsible for GDM/SDDM, PAM, SELinux and networking. The
// Ryoku installer only registers a separate Wayland session and installs the
// in-session qylock payload. In particular this function must never:
//   - disable/enable a display manager;
//   - edit /etc/pam.d;
//   - write /etc/sddm.conf*;
//   - change NetworkManager's backend;
//   - install or change GPU drivers.
func stepSessionFedora(e *engine) error {
	if !e.dry && !has("Hyprland") {
		return fmt.Errorf("Fedora M1 requires Hyprland to be installed before session registration; use the preflight tool and the pinned Ryoku Hyprland stack when available")
	}

	if e.p.switchDM || e.p.greeter || e.p.switchNet || e.p.nvidia {
		e.say("Fedora safety policy: ignoring host-owned display-manager, greeter, network and GPU toggles")
	}

	e.say("Fedora host policy: keeping the current display manager, PAM, SELinux and network configuration")

	sessionDir := "/usr/share/wayland-sessions"
	sessionFile := filepath.Join(sessionDir, "ryoku.desktop")
	if err := e.sudo("mkdir", "-p", sessionDir); err != nil {
		return err
	}
	if err := e.sudoWrite(sessionFile, fedoraSessionDesktop); err != nil {
		return err
	}
	// Fedora installs SELinux labels from policy/file-context rules. A file
	// created by tee normally receives the directory's expected type, and this
	// best-effort restorecon makes that explicit without weakening SELinux.
	if has("restorecon") {
		if err := e.sudo("restorecon", "-F", sessionFile); err != nil {
			e.say("warning: restorecon failed for "+sessionFile+"; SELinux remains enabled")
		}
	}
	e.recordRestore("sudo rm -f " + sessionFile)
	e.say("registered Ryoku as a separate Wayland login session")

	// qylock's user-only mode deliberately skips /usr/share/sddm/themes and
	// /etc/sddm.conf.d. It installs only the in-session lockscreen under HOME.
	lockScript := filepath.Join(e.payload, "ryoku/lockscreen/install-qylock")
	lockBundle := filepath.Join(e.payload, "ryoku/lockscreen/qylock")
	if err := e.cmd("", []string{
		"RYOKU_QYLOCK_USER_ONLY=1",
		"RYOKU_QYLOCK_BUNDLE=" + lockBundle,
	}, "bash", lockScript); err != nil {
		return err
	}
	e.say("installed the Ryoku in-session lockscreen without changing the Fedora greeter")

	if !e.f.nmEnabled {
		e.say("warning: NetworkManager is not enabled; Ryoku will not alter Fedora networking automatically")
	}
	if len(e.f.desktops) > 0 {
		e.sayf("%s stays installed and selectable from the existing login manager",
			joinDesktopNames(e.f.desktops))
	}
	return nil
}

// Kept tiny so session policy tests do not need to duplicate display-manager
// formatting logic.
func joinDesktopNames(v []string) string {
	if len(v) == 0 {
		return ""
	}
	out := v[0]
	for _, s := range v[1:] {
		out += ", " + s
	}
	return out
}
