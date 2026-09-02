package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const (
	fedoraSessionPath   = "/usr/share/wayland-sessions/ryoku.desktop"
	fedoraSessionMarker = "X-Ryoku-Fedora=1"
)

func isFedoraFacts(f *facts) bool {
	return f != nil && f.distro != nil && f.distro.id == "fedora"
}

// Fedora's first milestone is an overlay desktop, not a distro conversion.
// Defaults therefore keep every host-owned system choice untouched.
func fedoraDefaultPlan(f *facts) *plan {
	return &plan{
		monPins:  len(f.monOutputs) > 0,
		devtools: false,
		resume:   f.prevRun != nil,
	}
}

// The Fedora TUI only exposes switches whose effects are user-scoped or package
// installation-only. In particular it never offers SDDM, PAM, networking,
// NVIDIA-driver, AUR, rival-package removal, or login-shell mutation.
func buildFedoraItems(f *facts, p *plan) []planItem {
	var it []planItem
	if f.prevRun != nil {
		it = append(it, planItem{
			"Resume the previous run",
			fmt.Sprintf("%d step(s) already finished last time; keeps that run's backup dir and skips them", len(f.prevRun.Completed)),
			&p.resume,
			false,
		})
	}
	if len(f.monOutputs) > 0 {
		it = append(it, planItem{
			"Carry over monitor layout",
			fmt.Sprintf("pins %d output(s) from your %s setup into monitors_user.lua", len(f.monOutputs), f.monSource),
			&p.monPins,
			false,
		})
	}
	it = append(it, planItem{
		"Developer toolchain",
		"optional Go/Rust/Node/Python tools; Fedora packages only, no AUR",
		&p.devtools,
		false,
	})
	return it
}

// stepSessionFedora performs the one system-scoped action M1 actually needs:
// register a selectable Wayland session. It intentionally leaves the active
// display manager, PAM, network stack, SELinux policy and greeter untouched.
func stepSessionFedora(e *engine) error {
	if !e.dry && !has("Hyprland") {
		return fmt.Errorf("Hyprland is required before registering the Fedora Ryoku session")
	}

	if b, err := os.ReadFile(fedoraSessionPath); err == nil &&
		!strings.Contains(string(b), fedoraSessionMarker) {
		return fmt.Errorf("%s already exists and is not managed by Ryoku-on-Fedora; refusing to overwrite it", fedoraSessionPath)
	}

	session := "[Desktop Entry]\n" +
		"Name=Ryoku\n" +
		"Comment=Ryoku desktop on Fedora\n" +
		"Exec=Hyprland\n" +
		"TryExec=Hyprland\n" +
		"Type=Application\n" +
		"DesktopNames=Hyprland;Ryoku;\n" +
		fedoraSessionMarker + "\n"
	if err := e.sudoWrite(fedoraSessionPath, session); err != nil {
		return err
	}
	e.recordRestore("sudo rm -f " + fedoraSessionPath)

	// A file created under /usr/share should receive the directory's default
	// label, but explicitly restore it on SELinux hosts so enforcing mode is a
	// tested requirement rather than something users are told to disable.
	if !e.dry && has("restorecon") {
		if err := e.sudo("restorecon", "-F", fedoraSessionPath); err != nil {
			return fmt.Errorf("restore SELinux context on %s: %w", fedoraSessionPath, err)
		}
	}

	// The source deploy already installs this user-only lock, but repeat the
	// idempotent user half here so the session step owns its own invariant.
	lockScript := filepath.Join(e.payload, "ryoku/lockscreen/install-qylock")
	if err := e.cmd("", []string{"RYOKU_QYLOCK_USER_ONLY=1"}, "bash", lockScript); err != nil {
		return err
	}

	e.say("Fedora host preserved: existing display manager, PAM, SELinux and network policy were not changed")
	e.say("registered the Ryoku session; log out and select Ryoku in your existing login manager")
	if len(e.f.desktops) > 0 {
		e.sayf("%s stays installed and selectable alongside Ryoku", strings.Join(e.f.desktops, ", "))
	}
	return nil
}
