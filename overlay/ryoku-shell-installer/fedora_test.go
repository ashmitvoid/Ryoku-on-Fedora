package main

import (
	"strings"
	"testing"
)

func TestFedoraSafePlan(t *testing.T) {
	f := &facts{
		distro:    fedoraLinux,
		hasNvidia: true,
		userShell: "/bin/bash",
		currentDM: "gdm.service",
		otherNet:  []string{"systemd-networkd.service"},
	}
	p := defaultPlan(f)

	if p.nvidia || p.switchDM || p.switchNet || p.rivals || p.softOff || p.aur || p.fish || p.greeter {
		t.Fatalf("Fedora default plan crossed host-preserving boundary: %+v", *p)
	}

	p.nvidia, p.switchDM, p.switchNet, p.rivals, p.softOff, p.aur, p.fish, p.greeter =
		true, true, true, true, true, true, true, true
	enforceFedoraSafePlan(f, p)
	if p.nvidia || p.switchDM || p.switchNet || p.rivals || p.softOff || p.aur || p.fish || p.greeter {
		t.Fatalf("Fedora plan normalization failed: %+v", *p)
	}
}

func TestFedoraPlanDoesNotOfferHostMutationToggles(t *testing.T) {
	f := &facts{
		distro:    fedoraLinux,
		hasNvidia: true,
		userShell: "/bin/bash",
		currentDM: "gdm.service",
		otherNet:  []string{"systemd-networkd.service"},
		rivalPkgs: []string{"caelestia-shell"},
		softUnits: []string{"waybar.service"},
		kbLayout:  "us",
	}
	p := defaultPlan(f)
	items := buildItems(f, p)

	forbidden := []string{
		"NVIDIA proprietary drivers",
		"Switch login to SDDM",
		"Enable SDDM login",
		"Ryoku greeter theme",
		"Switch to NetworkManager",
		"Remove rival shells",
		"Disable conflicting daemons",
		"AUR extras",
		"fish as login shell",
		"AZERTY keyboard",
	}
	for _, it := range items {
		for _, bad := range forbidden {
			if strings.Contains(it.label, bad) {
				t.Fatalf("Fedora plan exposed host-mutating toggle %q", it.label)
			}
		}
	}
}

func TestFedoraSessionDesktop(t *testing.T) {
	s := fedoraSessionDesktop()
	for _, want := range []string{
		"Name=Ryoku",
		"Exec=Hyprland",
		"TryExec=Hyprland",
		fedoraSessionMarker,
	} {
		if !strings.Contains(s, want) {
			t.Fatalf("session desktop missing %q", want)
		}
	}
	if strings.Contains(strings.ToLower(s), "sddm") {
		t.Fatal("Fedora session registration must not depend on SDDM")
	}
}
