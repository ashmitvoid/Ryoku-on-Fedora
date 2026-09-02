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

func payloadSparsePathsFor(d *distro) []string {
	if d == nil || !d.fromSource {
		return sparsePaths
	}
	out := append([]string{}, sparsePaths...)
	out = append(out,
		"ryoku/shell",
		"ryoku/hyprland",
		"ryoku/hub",
		"ryoku/rashin",
		"ryoku/cli",
		"ryoku/ui",
		"system/hardware",
		"system/extras",
		"system/containers",
	)
	return out
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


func fedoraReplaceOnce(s, old, new, label string) (string, error) {
	if n := strings.Count(s, old); n != 1 {
		return "", fmt.Errorf("%s: expected one deploy.sh anchor, found %d", label, n)
	}
	return strings.Replace(s, old, new, 1), nil
}

func fedoraReplaceFirst(s, old, new, label string) (string, error) {
	if !strings.Contains(s, old) {
		return "", fmt.Errorf("%s: deploy.sh anchor not found", label)
	}
	return strings.Replace(s, old, new, 1), nil
}

func patchFedoraDeployText(s string) (string, error) {
	if strings.Contains(s, "host_preserve=\"${RYOKU_HOST_PRESERVE:-0}\"") {
		return s, nil
	}
	var err error

	s, err = fedoraReplaceOnce(s,
		"reload=1\n[[ \"${1:-}\" == \"--no-reload\" ]] && reload=0\n",
		"reload=1\n[[ \"${1:-}\" == \"--no-reload\" ]] && reload=0\nhost_preserve=\"${RYOKU_HOST_PRESERVE:-0}\"\n",
		"host preserve flag")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"  printf '    install it:  sudo pacman -S --needed go\\n' >&2\n",
		"  if (( host_preserve )); then\n    printf '    install it:  sudo dnf install golang\\n' >&2\n  else\n    printf '    install it:  sudo pacman -S --needed go\\n' >&2\n  fi\n",
		"Go install hint")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"for s in \"$here/../../system/extras\"/ryoku-*; do\n  install -m755 \"$s\" \"$bindir/${s##*/}\"\ndone\n# the extras actuator (renamed from ryoku-extras-install); the ryoku-* glob\n# above no longer matches it, so install it by name.\ninstall -m755 \"$here/../../system/extras/ryostore-install\" \"$bindir/ryostore-install\"\n",
		"if (( ! host_preserve )); then\n  for s in \"$here/../../system/extras\"/ryoku-*; do\n    install -m755 \"$s\" \"$bindir/${s##*/}\"\n  done\n  install -m755 \"$here/../../system/extras/ryostore-install\" \"$bindir/ryostore-install\"\nelse\n  say \"host-preserving mode: skipped Arch package actuators (RyoStore system installs stay disabled)\"\nfi\n",
		"Arch package actuators")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceFirst(s,
		"if command -v sudo >/dev/null 2>&1; then\n",
		"if (( ! host_preserve )) && command -v sudo >/dev/null 2>&1; then\n",
		"privileged host block")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"qtver=\"$(pacman -Q qt6-base 2>/dev/null | awk '{print $2}')\"\n",
		"qtver=\"$(pkg-config --modversion Qt6Core 2>/dev/null || pacman -Q qt6-base 2>/dev/null | awk '{print $2}')\"\n",
		"Qt version detection")
	if err != nil {
		return "", err
	}

	return s, nil
}

func prepareFedoraPayload(e *engine) error {
	if !isFedoraHost(e.f) {
		return nil
	}
	path := filepath.Join(e.payload, "ryoku", "shell", "deploy.sh")
	if e.dry {
		e.say("DRYRUN: apply Fedora host-preserving overlay to " + path)
		return nil
	}

	b, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("read Fedora deploy payload: %w", err)
	}
	patched, err := patchFedoraDeployText(string(b))
	if err != nil {
		return err
	}
	st, err := os.Stat(path)
	if err != nil {
		return err
	}
	if err := os.WriteFile(path, []byte(patched), st.Mode().Perm()); err != nil {
		return fmt.Errorf("write Fedora deploy payload: %w", err)
	}
	e.say("prepared Fedora host-preserving source payload")
	return nil
}
