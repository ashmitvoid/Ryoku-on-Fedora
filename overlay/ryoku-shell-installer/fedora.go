package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const fedoraPinnedUpstream = "85cd1cbd1f9cd90f72283fbad9094772156ec4f3"
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
	p.azertyFR = false
	p.azertyBE = false
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

func stepPayloadFedora(e *engine) error {
	if e.payloadOverride != "" {
		e.payload = e.payloadOverride
		if _, err := os.Stat(filepath.Join(e.payload, "ryoku/lockscreen/install-qylock")); err != nil && !e.dry {
			return fmt.Errorf("payload override %s does not look like a ryoku-arch checkout", e.payload)
		}
		e.say("using Fedora payload override " + e.payload)
		return prepareFedoraPayload(e)
	}

	cache := os.Getenv("XDG_CACHE_HOME")
	if cache == "" {
		cache = filepath.Join(e.f.homeDir, ".cache")
	}
	e.payload = filepath.Join(cache, "ryoku-shell-install/repo")

	if e.dry {
		e.say("DRYRUN: fetch pinned Ryoku payload " + fedoraPinnedUpstream)
		return prepareFedoraPayload(e)
	}

	if err := os.MkdirAll(filepath.Dir(e.payload), 0o755); err != nil {
		return err
	}
	if _, err := os.Stat(filepath.Join(e.payload, ".git")); err != nil {
		if err := os.RemoveAll(e.payload); err != nil {
			return err
		}
		if err := os.MkdirAll(e.payload, 0o755); err != nil {
			return err
		}
		if err := e.cmd(e.payload, nil, "git", "init"); err != nil {
			return err
		}
		if err := e.cmd(e.payload, nil, "git", "remote", "add", "origin", repoURL); err != nil {
			return err
		}
	} else {
		if err := e.cmd(e.payload, nil, "git", "remote", "set-url", "origin", repoURL); err != nil {
			return err
		}
	}

	if err := e.cmd(e.payload, nil, "git", "fetch", "--depth=1", "origin", fedoraPinnedUpstream); err != nil {
		return err
	}
	if err := e.cmd(e.payload, nil, "git", "sparse-checkout", "init", "--cone"); err != nil {
		return err
	}
	paths := payloadSparsePathsFor(e.d())
	if err := e.cmd(e.payload, nil, "git", append([]string{"sparse-checkout", "set"}, paths...)...); err != nil {
		return err
	}
	if err := e.cmd(e.payload, nil, "git", "checkout", "-f", "FETCH_HEAD"); err != nil {
		return err
	}

	for _, rel := range []string{
		"system/packages/base.packages",
		"ryoku/shell/deploy.sh",
		"ryoku/lockscreen/install-qylock",
	} {
		if _, err := os.Stat(filepath.Join(e.payload, rel)); err != nil {
			return fmt.Errorf("pinned Fedora payload is incomplete (missing %s): %w", rel, err)
		}
	}
	return prepareFedoraPayload(e)
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


func stepConfigsFedora(e *engine) error {
	enforceFedoraSafePlan(e.f, e.p)
	e.say("Fedora host-preserving mode: skipping broad ryoku materialize; finalizing Ryoku-owned config only")

	// deploy.sh already laid the Ryoku Hyprland and Quickshell trees. Keep this
	// step deliberately narrow so GNOME/KDE-facing ~/.config files remain owned
	// by the existing Fedora desktop.
	hyprDir := filepath.Join(e.f.homeDir, ".config/hypr")
	if !e.dry {
		if st, err := os.Stat(hyprDir); err != nil || !st.IsDir() {
			return fmt.Errorf("Fedora Ryoku config is missing after source deploy: %s", hyprDir)
		}
	}

	// Preserve a detected monitor layout only inside Ryoku's Hyprland config.
	if e.p.monPins && len(e.f.monOutputs) > 0 {
		pins, skipped := renderPins(e.f.monOutputs, e.f.monSource == "hyprland", e.f.monSource)
		for _, name := range skipped {
			e.sayf("note: %s output %q needs a connector pin in monitors_user.lua", e.f.monSource, name)
		}
		if pins != "" {
			mu := filepath.Join(hyprDir, "monitors_user.lua")
			if e.dry {
				e.say("DRYRUN: write Ryoku-only monitor pins to ~/.config/hypr/monitors_user.lua")
			} else if _, err := os.Lstat(mu); os.IsNotExist(err) {
				if err := os.WriteFile(mu, []byte(pins), 0o644); err != nil {
					return err
				}
			}
		}
	}

	// Carry a non-default keyboard layout into the Ryoku session only. Fedora's
	// console, GDM, PAM and Xorg keyboard policy remain untouched.
	if e.f.kbLayout != "" && (e.f.kbLayout != "us" || e.f.kbVariant != "" || e.f.kbOptions != "") {
		kb := filepath.Join(hyprDir, "keyboard.lua")
		if e.dry {
			e.say("DRYRUN: seed Ryoku-only keyboard layout in ~/.config/hypr/keyboard.lua")
		} else if _, err := os.Lstat(kb); os.IsNotExist(err) {
			clean := func(v string) string {
				return strings.NewReplacer("\"", "", "\\", "").Replace(v)
			}
			content := "-- keyboard layout carried into the Ryoku session by Ryoku-on-Fedora\n" +
				"hl.config({\n    input = {\n        kb_layout = \"" + clean(e.f.kbLayout) + "\",\n" +
				"        kb_variant = \"" + clean(e.f.kbVariant) + "\",\n" +
				"        kb_options = \"" + clean(e.f.kbOptions) + "\",\n    },\n})\n"
			if err := os.WriteFile(kb, []byte(content), 0o644); err != nil {
				return err
			}
		}
	}

	stubs := []struct{ rel, content string }{
		{"monitors_user.lua", "-- hand-pinned displays; pins here win.\n"},
		{"user.lua", "-- your Ryoku Hyprland overrides.\n"},
		{"theme.lua", "-- owned by Ryoku Settings.\n"},
		{"settings.lua", "-- owned by Ryoku Settings.\n"},
		{"modules/private.lua", "-- optional private Ryoku module.\n"},
		{"ghosttype.lua", "-- owned by ghosttype when installed.\n"},
	}
	for _, stub := range stubs {
		p := filepath.Join(hyprDir, stub.rel)
		if e.dry {
			e.say("DRYRUN: stub ~/.config/hypr/" + stub.rel + " if absent")
			continue
		}
		if _, err := os.Lstat(p); err == nil {
			continue
		}
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			return err
		}
		if err := os.WriteFile(p, []byte(stub.content), 0o644); err != nil {
			return err
		}
	}

	return e.cmd("", nil, "systemctl", "--user", "daemon-reload")
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
		"for s in \"$here/../../system/hardware\"/*/ryoku-* \"$here/../../system/containers\"/ryoku-*; do\n  [[ -f $s && -x $s ]] || continue\n  install -m755 \"$s\" \"$bindir/${s##*/}\"\ndone\n",
		"if (( ! host_preserve )); then\n  for s in \"$here/../../system/hardware\"/*/ryoku-* \"$here/../../system/containers\"/ryoku-*; do\n    [[ -f $s && -x $s ]] || continue\n    install -m755 \"$s\" \"$bindir/${s##*/}\"\n  done\nelse\n  say \"host-preserving mode: skipped Arch hardware/container actuators\"\nfi\n",
		"hardware actuators")
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

	s, err = fedoraReplaceOnce(s,
		"install -m755 \"$here/../cli/ryoku\" \"$bindir/ryoku\"\n",
		"install -m755 \"$here/../cli/ryoku\" \"$bindir/ryoku\"\nif (( host_preserve )); then\n  mv -f \"$bindir/ryoku\" \"$bindir/ryoku.real\"\n  cat > \"$bindir/ryoku\" <<'EOF'\n#!/usr/bin/env bash\nset -euo pipefail\ncase \"${1:-}\" in\n  update|doctor|recovery|rollback|snapshots|track|deploy|security-key|keyboard)\n    printf 'ryoku: %s is temporarily disabled by Ryoku-on-Fedora Phase 1; Fedora still owns system management.\\n' \"${1:-command}\" >&2\n    exit 2\n    ;;\nesac\nexec \"$(dirname \"$0\")/ryoku.real\" \"$@\"\nEOF\n  chmod 0755 \"$bindir/ryoku\"\n  say \"installed Fedora safety wrapper around Arch system-management CLI commands\"\nfi\n",
		"Fedora CLI guard")
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
		"qtver=\"\"\nif command -v qtpaths6 >/dev/null 2>&1; then\n  qtver=\"$(qtpaths6 --qt-version 2>/dev/null || true)\"\nelif pkg-config --exists Qt6Core 2>/dev/null; then\n  qtver=\"$(pkg-config --modversion Qt6Core 2>/dev/null || true)\"\nelif command -v pacman >/dev/null 2>&1; then\n  qtver=\"$(pacman -Q qt6-base 2>/dev/null | awk '{print $2}')\"\nfi\n",
		"Qt version detection")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"if command -v makepkg >/dev/null 2>&1 && pkg-config --exists hyprland 2>/dev/null; then\n",
		"if (( ! host_preserve )) && command -v makepkg >/dev/null 2>&1 && pkg-config --exists hyprland 2>/dev/null; then\n",
		"Hyprland plugin packaging")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"install -Dm644 \"$here/portals/hyprland-portals.conf\" \"$cfg/xdg-desktop-portal/hyprland-portals.conf\"\n",
		"if (( ! host_preserve )); then\n  install -Dm644 \"$here/portals/hyprland-portals.conf\" \"$cfg/xdg-desktop-portal/hyprland-portals.conf\"\nelse\n  say \"host-preserving mode: keeping the host user portal policy untouched\"\nfi\n",
		"portal policy")
	if err != nil {
		return "", err
	}


	s, err = fedoraReplaceOnce(s,
		"install -Dm644 \"$here/../apps/spicetify/ryoku-canvas.js\" \"$cfg/spicetify/Extensions/ryoku-canvas.js\"\nsay \"installed ryoku-canvas spicetify extension\"\n",
		"if (( ! host_preserve )); then\n  install -Dm644 \"$here/../apps/spicetify/ryoku-canvas.js\" \"$cfg/spicetify/Extensions/ryoku-canvas.js\"\n  say \"installed ryoku-canvas spicetify extension\"\nelse\n  say \"host-preserving mode: skipped Spicetify extension injection\"\nfi\n",
		"Spicetify injection")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"install -Dm644 \"$here/../apps/nautilus/ryoku-stash-menu.py\" \\\n  \"$appshare/nautilus-python/extensions/ryoku-stash-menu.py\"\nsay \"installed nautilus stash menu -> $appshare/nautilus-python/extensions\"\n",
		"if (( ! host_preserve )); then\n  install -Dm644 \"$here/../apps/nautilus/ryoku-stash-menu.py\" \\\n    \"$appshare/nautilus-python/extensions/ryoku-stash-menu.py\"\n  say \"installed nautilus stash menu -> $appshare/nautilus-python/extensions\"\nelse\n  say \"host-preserving mode: skipped Nautilus extension injection\"\nfi\n",
		"Nautilus injection")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"cp -a \"$here/../apps/fish/config.fish\" \"$cfg/fish/config.fish\"\nmkdir -p \"$cfg/fish/conf.d\"; cp -a \"$here/../apps/fish/conf.d/.\" \"$cfg/fish/conf.d/\"\nmkdir -p \"$cfg/ryoku-terminal\"; cp -a \"$here/../apps/terminal-shell/.\" \"$cfg/ryoku-terminal/\"\nmkdir -p \"$cfg/bash\"; cp -a \"$here/../apps/bash/.\" \"$cfg/bash/\"\nmkdir -p \"$cfg/zsh\"; cp -a \"$here/../apps/zsh/.\" \"$cfg/zsh/\"\nmkdir -p \"$cfg/qt6ct\"; cp -a \"$here/qt6ct/qt6ct.conf\" \"$cfg/qt6ct/qt6ct.conf\"\n",
		"mkdir -p \"$cfg/ryoku-terminal\"; cp -a \"$here/../apps/terminal-shell/.\" \"$cfg/ryoku-terminal/\"\nif (( ! host_preserve )); then\n  cp -a \"$here/../apps/fish/config.fish\" \"$cfg/fish/config.fish\"\n  mkdir -p \"$cfg/fish/conf.d\"; cp -a \"$here/../apps/fish/conf.d/.\" \"$cfg/fish/conf.d/\"\n  mkdir -p \"$cfg/bash\"; cp -a \"$here/../apps/bash/.\" \"$cfg/bash/\"\n  mkdir -p \"$cfg/zsh\"; cp -a \"$here/../apps/zsh/.\" \"$cfg/zsh/\"\n  mkdir -p \"$cfg/qt6ct\"; cp -a \"$here/qt6ct/qt6ct.conf\" \"$cfg/qt6ct/qt6ct.conf\"\nelse\n  say \"host-preserving mode: kept Fish/Bash/Zsh/Qt user configuration untouched\"\nfi\n",
		"shell and Qt user config")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"mkdir -p \"$cfg/gtk-3.0\"; cp -a \"$here/gtk-3.0/settings.ini\" \"$cfg/gtk-3.0/settings.ini\"\nmkdir -p \"$cfg/gtk-4.0\"; cp -a \"$here/gtk-4.0/settings.ini\" \"$cfg/gtk-4.0/settings.ini\"\nmkdir -p \"$cfg/btop\"; cp -a \"$here/../apps/btop/btop.conf\" \"$cfg/btop/btop.conf\"\nmkdir -p \"$cfg/fastfetch\"\ncp -a \"$here/../apps/fastfetch/config.jsonc\" \"$cfg/fastfetch/config.jsonc\"\ninstall -m755 \"$here/../apps/fastfetch/ryoku-fastfetch\" \"$bindir/ryoku-fastfetch\"\nmkdir -p \"$cfg/kitty\"\ncp -a \"$here/../apps/kitty/kitty.conf\" \"$cfg/kitty/kitty.conf\"\ncp -a \"$here/../apps/kitty/current-theme.conf\" \"$cfg/kitty/current-theme.conf\"\nmkdir -p \"$cfg/wireplumber\"; cp -a \"$here/../apps/wireplumber/.\" \"$cfg/wireplumber/\"\n",
		"install -m755 \"$here/../apps/fastfetch/ryoku-fastfetch\" \"$bindir/ryoku-fastfetch\"\nif (( ! host_preserve )); then\n  mkdir -p \"$cfg/gtk-3.0\"; cp -a \"$here/gtk-3.0/settings.ini\" \"$cfg/gtk-3.0/settings.ini\"\n  mkdir -p \"$cfg/gtk-4.0\"; cp -a \"$here/gtk-4.0/settings.ini\" \"$cfg/gtk-4.0/settings.ini\"\n  mkdir -p \"$cfg/btop\"; cp -a \"$here/../apps/btop/btop.conf\" \"$cfg/btop/btop.conf\"\n  mkdir -p \"$cfg/fastfetch\"; cp -a \"$here/../apps/fastfetch/config.jsonc\" \"$cfg/fastfetch/config.jsonc\"\n  mkdir -p \"$cfg/kitty\"\n  cp -a \"$here/../apps/kitty/kitty.conf\" \"$cfg/kitty/kitty.conf\"\n  cp -a \"$here/../apps/kitty/current-theme.conf\" \"$cfg/kitty/current-theme.conf\"\n  mkdir -p \"$cfg/wireplumber\"; cp -a \"$here/../apps/wireplumber/.\" \"$cfg/wireplumber/\"\nelse\n  say \"host-preserving mode: kept GTK/Btop/Fastfetch/Kitty/WirePlumber user configuration untouched\"\nfi\n",
		"shared desktop app config")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"systemctl --user try-restart ryogami.service 2>/dev/null || true\n",
		"if (( ! host_preserve )); then\n  systemctl --user try-restart ryogami.service 2>/dev/null || true\nfi\n",
		"Ryogami restart")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"systemctl --user enable --now ryoku-ai-usage.timer 2>/dev/null || true\n",
		"if (( ! host_preserve )); then\n  systemctl --user enable --now ryoku-ai-usage.timer 2>/dev/null || true\nelse\n  say \"host-preserving mode: Ryoku background timers remain disabled outside the Ryoku session\"\nfi\n",
		"AI usage timer")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"mkdir -p \"$cfg/pip\"; cp -a \"$here/../apps/pip/pip.conf\" \"$cfg/pip/pip.conf\"\n",
		"if (( ! host_preserve )); then\n  mkdir -p \"$cfg/pip\"; cp -a \"$here/../apps/pip/pip.conf\" \"$cfg/pip/pip.conf\"\nelse\n  say \"host-preserving mode: kept pip user configuration untouched\"\nfi\n",
		"pip config")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"if command -v sudo >/dev/null 2>&1; then\n  cmp -s \"$here/../apps/mimeapps.list\" /usr/share/applications/mimeapps.list ||\n    sudo install -Dm644 \"$here/../apps/mimeapps.list\" /usr/share/applications/mimeapps.list || true\nfi\n",
		"if (( ! host_preserve )) && command -v sudo >/dev/null 2>&1; then\n  cmp -s \"$here/../apps/mimeapps.list\" /usr/share/applications/mimeapps.list ||\n    sudo install -Dm644 \"$here/../apps/mimeapps.list\" /usr/share/applications/mimeapps.list || true\nelif (( host_preserve )); then\n  say \"host-preserving mode: kept Fedora system MIME defaults untouched\"\nfi\n",
		"MIME defaults")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"cp -a \"$here/../apps/chromium-flags.conf\" \"$cfg/chromium-flags.conf\"\n",
		"if (( ! host_preserve )); then\n  cp -a \"$here/../apps/chromium-flags.conf\" \"$cfg/chromium-flags.conf\"\nelse\n  say \"host-preserving mode: kept Chromium flags untouched\"\nfi\n",
		"Chromium flags")
	if err != nil {
		return "", err
	}

	s, err = fedoraReplaceOnce(s,
		"if [[ -f \"$_iconroot/index.theme\" ]] && command -v gtk-update-icon-cache >/dev/null 2>&1; then\n  gtk-update-icon-cache -qtf \"$_iconroot\" 2>/dev/null || true\nelse\n  rm -f \"$_iconroot/icon-theme.cache\" 2>/dev/null || true\nfi\n",
		"if (( ! host_preserve )); then\n  if [[ -f \"$_iconroot/index.theme\" ]] && command -v gtk-update-icon-cache >/dev/null 2>&1; then\n    gtk-update-icon-cache -qtf \"$_iconroot\" 2>/dev/null || true\n  else\n    rm -f \"$_iconroot/icon-theme.cache\" 2>/dev/null || true\n  fi\nelse\n  say \"host-preserving mode: kept the host user icon cache untouched\"\nfi\n",
		"user icon cache")
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
