package main

import (
	"strings"
	"testing"
)

func TestFedoraDefaultPlanPreservesHost(t *testing.T) {
	f := &facts{
		distro:     fedoraLinux,
		hasNvidia:  true,
		currentDM:  "gdm.service",
		otherNet:   []string{"systemd-networkd.service"},
		userShell:  "/bin/bash",
		kbLayout:   "us",
	}
	p := defaultPlan(f)
	if p.nvidia || p.switchDM || p.switchNet || p.greeter || p.aur {
		t.Fatalf("Fedora host-owned toggles must default off: %+v", *p)
	}
}

func TestFedoraPlanHidesHostMutationToggles(t *testing.T) {
	f := &facts{
		distro:     fedoraLinux,
		hasNvidia:  true,
		currentDM:  "gdm.service",
		otherNet:   []string{"systemd-networkd.service"},
		userShell:  "/bin/bash",
		kbLayout:   "us",
	}
	p := defaultPlan(f)
	items := buildItems(f, p)
	var labels []string
	for _, it := range items {
		labels = append(labels, it.label)
	}
	got := strings.Join(labels, "\n")
	for _, forbidden := range []string{
		"NVIDIA proprietary drivers",
		"Switch login to SDDM",
		"Enable SDDM login",
		"Ryoku greeter theme",
		"Switch to NetworkManager",
		"AZERTY keyboard (French)",
		"AZERTY keyboard (Belgian)",
		"AUR extras",
	} {
		if strings.Contains(got, forbidden) {
			t.Fatalf("Fedora plan unexpectedly exposes %q:\n%s", forbidden, got)
		}
	}
}

func TestFedoraSourceStepList(t *testing.T) {
	e := newEngine(&facts{distro: fedoraLinux}, &plan{}, true, "", "")
	var ids []string
	for _, s := range e.steps {
		ids = append(ids, s.id)
	}
	got := strings.Join(ids, " ")
	want := "sysupgrade tools payload backup conflicts packages build session configs shell doctor verify"
	if got != want {
		t.Fatalf("Fedora steps = %q want %q", got, want)
	}
}

func TestFedoraSessionDesktop(t *testing.T) {
	for _, want := range []string{
		"Name=Ryoku",
		"Exec=Hyprland",
		"TryExec=Hyprland",
		"DesktopNames=Hyprland;Ryoku",
	} {
		if !strings.Contains(fedoraSessionDesktop, want) {
			t.Fatalf("session desktop missing %q", want)
		}
	}
	if strings.Contains(strings.ToLower(fedoraSessionDesktop), "sddm") {
		t.Fatal("Fedora session registration must not depend on SDDM")
	}
}
