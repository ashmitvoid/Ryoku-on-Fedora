package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const fedoraSessionPath = "/usr/share/wayland-sessions/ryoku.desktop"
const fedoraSessionMarker = "X-Ryoku-Fedora-Port=true"

func isFedoraHost(f *facts) bool {
	return f != nil && f.distro != nil && f.distro.id == "fedora"
}

func enforceFedoraSafePlan(f *facts, p *plan) {
	if !isFedoraHost(f) || p == nil {
		return
	}
	p.nvidia = false
	p.switchDM = false
	p.switchNet = false
	p.rivals = false
	p.softOff = false
	p.aur = false
	p.fish = false
	p.greeter = false
}

func fedoraSessionDesktop() string {
	return "[Desktop Entry]\n" +
		"Name=Ryoku\n" +
		"Comment=Ryoku Desktop (Hyprland + Quickshell)\n" +
		"Exec=Hyprland\n" +
		"TryExec=Hyprland\n" +
		"Type=Application\n" +
		"DesktopNames=Hyprland\n" +
		fedoraSessionMarker + "\n"
}

func stepSessionFedora(e *engine) error {
	enforceFedoraSafePlan(e.f, e.p)
	e.say("Fedora host-preserving mode: keeping the current display manager, PAM, SELinux and network policy")

	lockInstaller := filepath.Join(e.payload, "ryoku/lockscreen/install-qylock")
	lockBundle := filepath.Join(e.payload, "ryoku/lockscreen/qylock")
	if err := e.cmd("", []string{
		"RYOKU_QYLOCK_USER_ONLY=1",
		"RYOKU_QYLOCK_BUNDLE=" + lockBundle,
	}, "bash", lockInstaller); err != nil {
		return err
	}

	if !e.dry {
		if b, err := os.ReadFile(fedoraSessionPath); err == nil {
			if !strings.Contains(string(b), fedoraSessionMarker) {
				return fmt.Errorf("%s already exists and is not managed by Ryoku-on-Fedora; refusing to overwrite it", fedoraSessionPath)
			}
		} else if !os.IsNotExist(err) {
			return fmt.Errorf("inspect %s: %w", fedoraSessionPath, err)
		}
	}

	if err := e.sudo("mkdir", "-p", filepath.Dir(fedoraSessionPath)); err != nil {
		return err
	}
	if err := e.sudoWrite(fedoraSessionPath, fedoraSessionDesktop()); err != nil {
		return err
	}
	if err := e.sudo("chmod", "0644", fedoraSessionPath); err != nil {
		return err
	}
	if has("restorecon") {
		if err := e.sudo("restorecon", "-F", fedoraSessionPath); err != nil {
			return err
		}
	}
	e.recordRestore("sudo rm -f " + fedoraSessionPath)

	if len(e.f.desktops) > 0 {
		e.sayf("%s stays installed; Ryoku is added as another session at the existing login screen",
			strings.Join(e.f.desktops, ", "))
	} else {
		e.say("registered Ryoku as a separate Wayland session in the existing display manager")
	}
	return nil
}
