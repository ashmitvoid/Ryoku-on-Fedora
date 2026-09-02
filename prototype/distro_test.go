package main

import (
	"strings"
	"testing"
)

// Minimal upstream type/function stubs so this isolated adapter prototype can
// be unit-tested without reconstructing the whole Ryoku installer package.
type facts struct {
	distro  *distro
	homeDir string
}

type engine struct{ f *facts }

func parseOSRelease(string) (string, string, string) { return "", "", "" }

func TestDetectFedora(t *testing.T) {
	for _, c := range []struct {
		id, like, want string
	}{
		{"arch", "", "arch"},
		{"ubuntu", "debian", "debian"},
		{"fedora", "", "fedora"},
		{"nobara", "fedora", "fedora"},
		{"ultramarine", "fedora", "fedora"},
		{"void", "", ""},
	} {
		d := detectDistro(c.id, c.like)
		got := ""
		if d != nil {
			got = d.id
		}
		if got != c.want {
			t.Fatalf("detectDistro(%q,%q)=%q want %q", c.id, c.like, got, c.want)
		}
	}
}

func TestFedoraCommands(t *testing.T) {
	if got := strings.Join(fedoraLinux.installArgs([]string{"git"}), " "); got != "dnf -y install git" {
		t.Fatalf("install args = %q", got)
	}
	if got := strings.Join(fedoraLinux.removeArgs([]string{"dunst"}), " "); got != "dnf -y remove dunst" {
		t.Fatalf("remove args = %q", got)
	}
}

func TestFedoraMapFailsClosed(t *testing.T) {
	if got := fedoraLinux.local("networkmanager"); got != "NetworkManager" {
		t.Fatalf("networkmanager maps to %q", got)
	}
	if got := fedoraLinux.local("quickshell"); got != "quickshell" {
		t.Fatalf("quickshell maps to %q", got)
	}
	if got := fedoraLinux.local("definitely-an-arch-only-package"); got != "" {
		t.Fatalf("unmapped package should be skipped, got %q", got)
	}
	if got := fedoraLinux.local("hyprland"); got != "" {
		t.Fatalf("hyprland must stay out of the Fedora base map until Ryoku owns its ABI, got %q", got)
	}
}

func TestFedoraCoreBatch(t *testing.T) {
	in := []string{"networkmanager", "pipewire-pulse", "xorg-xwayland", "quickshell", "hyprland", "matugen"}
	got := fedoraLinux.localAll(in)
	want := []string{"NetworkManager", "pipewire-pulseaudio", "xorg-x11-server-Xwayland", "quickshell"}
	if strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("localAll = %v want %v", got, want)
	}
}
