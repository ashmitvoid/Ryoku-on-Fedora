package main

import (
	"os"
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

func TestSourcePayloadIncludesDeployInputs(t *testing.T) {
	paths := payloadSparsePathsFor(fedoraLinux)
	got := map[string]bool{}
	for _, p := range paths {
		got[p] = true
	}
	for _, want := range []string{
		"ryoku/shell",
		"ryoku/hyprland",
		"ryoku/hub",
		"ryoku/rashin",
		"ryoku/cli",
		"ryoku/ui",
		"system/hardware",
		"system/extras",
		"system/containers",
	} {
		if !got[want] {
			t.Fatalf("source payload missing %s", want)
		}
	}
}


func TestRuntimePayloadPatch(t *testing.T) {
	b, err := os.ReadFile("../ryoku/shell/deploy.sh")
	if err != nil {
		t.Fatalf("read upstream deploy.sh: %v", err)
	}
	patched, err := patchFedoraDeployText(string(b))
	if err != nil {
		t.Fatalf("patch Fedora deploy: %v", err)
	}
	for _, want := range []string{
		"host_preserve=\\\"${RYOKU_HOST_PRESERVE:-0}\\\"",
		"if (( ! host_preserve )) && command -v sudo",
		"skipped Arch hardware/container actuators",
		"skipped Arch package actuators",
		"installed Fedora safety wrapper around Arch system-management CLI commands",
		"update|doctor|recovery|rollback|snapshots|track|deploy|security-key|keyboard",
		"qtpaths6 --qt-version",
		"if (( ! host_preserve )) && command -v makepkg",
		"keeping host portal policy untouched",
	} {
		if !strings.Contains(patched, want) {
			t.Fatalf("runtime payload patch missing %q", want)
		}
	}
	again, err := patchFedoraDeployText(patched)
	if err != nil {
		t.Fatalf("runtime payload patch is not idempotent: %v", err)
	}
	if again != patched {
		t.Fatal("runtime payload patch changed an already patched deploy.sh")
	}
}


func TestFedoraPayloadIsPinned(t *testing.T) {
	const want = "85cd1cbd1f9cd90f72283fbad9094772156ec4f3"
	if fedoraPinnedUpstream != want {
		t.Fatalf("Fedora payload moved: got %s want %s", fedoraPinnedUpstream, want)
	}
}
