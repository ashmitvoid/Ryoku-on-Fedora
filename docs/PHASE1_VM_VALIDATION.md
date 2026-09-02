# Fedora 44 Phase 1 VM validation

This is the first destructive validation gate for Ryoku-on-Fedora. Use a disposable Fedora 44 Workstation VM, not a daily-use machine.

## What M1 is proving

Ryoku is added as another Wayland desktop while Fedora remains the operating system owner.

A successful test must prove both sides:

1. the Ryoku session boots and its core UI works; and
2. Fedora-owned state is unchanged.

A Ryoku session that renders but rewrites PAM, SELinux, GDM, NetworkManager, the kernel, or the boot chain is a failed port.

## VM baseline

Use Fedora 44 Workstation x86_64 with:

- SELinux **Enforcing**
- GDM enabled
- the stock Fedora kernel and boot chain
- NetworkManager enabled
- no pre-existing Ryoku files
- a VM snapshot taken before installation

The Phase 1 installer currently expects a usable Hyprland binary. Until the Ryoku-owned Hyprland RPM/COPR stack is ready, this remains the deliberate external blocker for a fully reproducible clean-VM install.

## 1. Capture the untouched Fedora baseline

Do this **before** installing the Ryoku compositor RPMs:

```bash
mkdir -p ~/.local/state/ryoku-fedora-test
bash tests/vm/capture-fedora-host-state.sh \
  ~/.local/state/ryoku-fedora-test/before.state
```

## 2. Install the Ryoku compositor artifact

Extract the `ryoku-hyprland-fedora44-rpms` artifact from a fully green CI run, then install only the compositor and portal:

```bash
bash tests/vm/install-compositor-rpms.sh /path/to/extracted-rpm-artifact
```

The helper disables weak dependencies and refuses to proceed if another Hyprland package is already installed. In particular, `hyprlock` must **not** be pulled in because M1 uses qylock and the Fedora PAM tree must remain unchanged.

## 3. Preflight

From a checkout of this repository's `phase1-safe-session` branch:

```bash
bash prototype/fedora-preflight.sh
```

Do not continue past a blocker. At this point Hyprland and the Hyprland portal should come from the Ryoku RPM stack.

The state file records hashes/identities for:

- running and installed kernel set
- SELinux enforcement/configuration
- systemd default target
- display-manager selection
- GDM/SDDM enablement
- NetworkManager enablement and configuration
- `/etc/pam.d`
- Fedora GRUB/EFI/loader state

## 5. Installer dry run

Use the integrated Fedora installer artifact from a green `Phase 1 Fedora integration` workflow, or build the same overlay locally.

First run:

```bash
./ryoku-shell-install --dry-run --yes
```

The plan must **not** contain operations that:

- install or enable SDDM
- edit PAM
- disable SELinux
- install GPU drivers
- run mkinitcpio
- touch Limine
- force NetworkManager to iwd
- remove the existing desktop
- remove rival packages
- use pacman, yay, or makepkg

## 4. Install

Only after the dry run is clean:

```bash
./ryoku-shell-install --yes
```

Expected system-level addition:

```text
/usr/share/wayland-sessions/ryoku.desktop
```

It must contain:

```text
X-Ryoku-Fedora-Port=true
```

The source deployment should otherwise remain user-scoped and stage the Ryoku configuration without reloading the currently running GNOME session.

## 6. Verify Fedora host preservation before logout

```bash
bash tests/vm/verify-fedora-host-preserved.sh \
  ~/.local/state/ryoku-fedora-test/before.state
```

This must pass with SELinux still Enforcing.

## 7. Login test

Log out normally. In GDM's session selector choose **Ryoku**.

Validate:

- Hyprland starts without emergency/config errors
- Ryoku Quickshell shell appears
- launcher opens
- Hub opens
- notifications render
- audio through PipeWire works
- NetworkManager connectivity is still available
- Bluetooth service is visible when the VM exposes Bluetooth
- qylock can invoke the in-session lock UI
- logout exits Hyprland and returns to the existing GDM greeter

Expected degraded Phase 1 features are acceptable when their Fedora backend is deliberately absent, especially Hyprland compositor plugins and the Hyprland portal backend.

## 8. Fedora fallback test

From GDM, log into **GNOME** again.

Confirm GNOME still starts normally and the machine remains managed as Fedora.

Run the preservation check again:

```bash
bash tests/vm/verify-fedora-host-preserved.sh \
  ~/.local/state/ryoku-fedora-test/before.state
```

## 9. CLI safety test

These commands are intentionally blocked in Phase 1 because their upstream implementations currently orchestrate Arch system policy:

```bash
ryoku update
ryoku doctor
ryoku recovery
ryoku rollback
ryoku snapshots
ryoku track
ryoku deploy
ryoku security-key
ryoku keyboard
```

They should exit with the Ryoku-on-Fedora guard message rather than invoking pacman/yay/snapper/PAM behavior.

User-scoped commands that do not cross that boundary remain available through the underlying Ryoku CLI.

## 10. Removal / rollback test

Stay in the **GNOME** fallback session. Do not run removal from inside Ryoku/Hyprland.

Run:

```bash
bash tests/vm/remove-phase1.sh \
  ~/.local/state/ryoku-fedora-test/before.state
```

The helper:

- runs the installer-generated `restore.sh`
- restores any pre-existing Hyprland/Quickshell/qylock configuration that was moved aside
- removes Ryoku-created user files when no pre-install version existed
- removes the managed `Ryoku` GDM session entry
- removes only `ryoku-xdg-desktop-portal-hyprland` and `ryoku-hyprland`
- does not autoremove Fedora dependencies
- verifies the original Fedora kernel, SELinux, GDM, PAM, NetworkManager and boot state again

After removal, reboot once and confirm Fedora returns directly to its original GDM/GNOME path.

## Pass criteria

M1 VM validation passes only when:

- Ryoku is selectable in the existing Fedora login manager
- Ryoku reaches a usable desktop
- GNOME remains usable as a fallback
- SELinux remains Enforcing
- the before/after host-preservation harness passes
- no Arch package/boot/driver manager was invoked
- the VM can reboot back into the original Fedora boot path
- the Phase 1 removal helper succeeds from GNOME
- the Ryoku session and Ryoku compositor RPMs are absent after removal
- the post-removal Fedora host-preservation check passes

After this gate, the next major blocker is replacing the externally supplied Hyprland with the Ryoku-owned Fedora RPM/COPR compositor + portal + plugin stack.
