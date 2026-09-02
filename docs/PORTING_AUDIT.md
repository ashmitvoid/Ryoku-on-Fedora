# Ryoku on Fedora — Phase 0 Porting Audit

Baseline pinned on 2026-09-02:

- Upstream: `neur0map/ryoku-arch`
- Branch: `unstable-dev`
- Version: `0.53.7-beta.19`
- Commit: `85cd1cbd1f9cd90f72283fbad9094772156ec4f3`
- Initial Fedora target: Fedora 44 x86_64
- Compatibility target: Fedora 45

## Porting contract

The Fedora port preserves the Ryoku desktop identity and behavior while Fedora keeps ownership of the host operating system.

Fedora-owned and therefore **not transplanted from Arch**:

- kernel and kernel update policy
- initramfs (`dracut`, not `mkinitcpio`)
- bootloader / EFI policy
- RPM/DNF database
- GPU driver policy
- SELinux policy and labels
- Fedora release upgrades

Ryoku-owned on Fedora:

- Hyprland/Ryoku session integration
- Ryoku Quickshell UI
- Ryoku Hub and first-party apps
- user configuration/materialization
- live theming and wallpaper integration
- Ryoku-specific helper binaries
- eventually a pinned Hyprland + compositor-plugin RPM/COPR stack
- eventually Fedora-native `ryoku update`, RyoStore package routing and doctor fixes

## Important upstream discovery

`ryoku-shell-installer/distro.go` already isolates package-manager behavior into a `distro` abstraction. Arch and Debian implementations exist today. This is the correct extension point for Fedora.

The source-based Debian path also gives Fedora an initial deployment model: clone the Ryoku payload, install distro-native dependencies, compile Go/QML components, and deploy user configuration without using the `[ryoku]` pacman repository.

## Work areas

### A. Installer distro abstraction — ACTIVE

Files:

- `ryoku-shell-installer/distro.go`
- `ryoku-shell-installer/distro_test.go`
- `ryoku-shell-installer/install.sh`

Phase-0 prototype adds:

- Fedora detection through `ID=fedora` or `ID_LIKE=fedora`
- DNF install/remove/update commands
- RPM installed-package queries
- source-build mode
- fail-closed Arch→Fedora package mapping
- Fedora 44/45 bootstrap messaging

Why fail closed: `system/packages/base.packages` is an Arch manifest. Passing an unknown Arch package name through unchanged can make one `dnf install` transaction fail. Fedora therefore skips unmapped names until they are verified or supplied by our COPR.

### B. Fedora package map — ACTIVE

Already confirmed as available in Fedora 44 and useful to Ryoku:

- `quickshell`
- `qt6-qtdeclarative-devel`
- `qt6-qtmultimedia-devel`
- `qt6-qtshadertools-devel`
- `qt6-qtsvg-devel`
- `qt6-qt5compat-devel`
- the standard Fedora Qt/Wayland/NetworkManager/PipeWire stack

Quickshell's Fedora package exposes Ryoku-critical QML modules including `Quickshell.Hyprland`, Bluetooth, MPRIS, PipeWire, notifications, PAM, Polkit, UPower and Wayland modules.

Still requires live Fedora `dnf repoquery` verification before a destructive installer run. The repository includes `prototype/fedora-preflight.sh` for this.

### C. Hyprland + compositor ABI — BLOCKER FOR PRODUCTION

Ryoku uses optional compositor plugins such as:

- dynamic-cursors
- hyprbars
- hyprfocus
- hyprglass
- imgborders

Upstream's source deploy intentionally builds these only when both `makepkg` and Hyprland development metadata exist. On non-Arch source installs they are skipped cleanly, so the shell can still be brought up for the first proof of concept.

Production Fedora must not depend on an arbitrary third-party Hyprland COPR. Plan: own a Ryoku Fedora COPR that builds a pinned Hyprland stack and all Ryoku plugins against the exact same ABI.

### D. Display manager / PAM / lockscreen — BLOCKER BEFORE REAL INSTALL TEST

`ryoku-shell-installer/engine.go::stepSession` is not distro-neutral today.

It can:

- disable the existing display manager
- enable SDDM
- execute `ryoku/lockscreen/sddm/setup`
- edit `/etc/pam.d/sddm`
- write SDDM drop-ins
- force a Weston-based SDDM Wayland greeter
- switch NetworkManager Wi-Fi to the iwd backend

Those operations were authored around the Ryoku Arch system and must **not** run unchanged on Fedora.

Initial Fedora policy:

- keep Fedora's current display manager (normally GDM on Workstation)
- do not edit Fedora PAM files
- do not disable SELinux
- do not replace Fedora network policy
- install only the in-session qylock side using `RYOKU_QYLOCK_USER_ONLY=1`
- register a `Ryoku` Wayland session separately

A Fedora-specific `stepSession` branch is the next code change before any live machine test.

### E. Ryoku CLI updater — MAJOR PORT

Current packaged updater is explicitly Arch-native:

- `pacman -Syu`
- `yay -Sua`
- pacman lock handling
- `snap-pac`
- Limine snapshot helpers
- package-version parsing from pacman

For Fedora we need a backend roughly equivalent to:

- `dnf upgrade --refresh`
- Fedora/Ryoku COPR package update
- Flatpak update (existing logic can remain)
- Fedora-safe rollback/update semantics
- no assumptions about Limine or `snap-pac`

Do not simply replace the word `pacman` with `dnf`; the snapshot and package lifecycle semantics differ.

### F. `ryoku doctor` — MAJOR PORT

Several reconcilers and fix strings are Arch-specific. Examples found in upstream include:

- pacman config reconciliation
- quickshell fix command using `pacman -S`
- ASUS Aura installation using pacman
- spicetify package fixes using the `[ryoku]` pacman repository
- package database reporting as `pacman + yay`

The source installer currently treats doctor findings as non-fatal, which lets the Phase-1 desktop proof of concept proceed, but production Fedora needs distro-aware doctor reconcilers.

### G. RyoStore / package helpers — MAJOR PORT

Current helpers route to:

- `ryoku-pkg-add` → pacman
- `ryoku-pkg-aur-add` → yay/paru
- `ryoku-pkg-remove` → pacman
- multilib and CachyOS repository mutation

Fedora needs a package-provider layer rather than AUR emulation. Candidate channels:

- Fedora repositories
- Ryoku COPR
- Flatpak
- source-only optional components where necessary

CachyOS and Arch multilib controls should not appear as Fedora actions.

## First milestone definition

**M1: Fedora 44 proof of concept** is complete only when all of these hold:

1. Fedora 44 remains bootable with its original kernel, bootloader and SELinux configuration.
2. Existing GNOME/KDE remains installed and selectable.
3. A separate `Ryoku` Wayland session is available in the existing display manager.
4. Logging into Ryoku starts Hyprland with the Ryoku Lua config and Quickshell shell.
5. Hub, launcher, bar/panels and basic theming render.
6. NetworkManager, PipeWire, Bluetooth and basic media controls function.
7. Logout returns to the existing Fedora display manager cleanly.
8. Uninstall/restore removes Ryoku user state without damaging the original desktop.
9. No `pacman`, `yay`, `makepkg`, `mkinitcpio` or Limine mutation is executed on Fedora.
10. SELinux remains Enforcing during validation.

Not required for M1:

- Ryoku compositor plugins
- production COPR
- Fedora-native `ryoku update`
- full RyoStore support
- custom Fedora ISO/spin

## Next implementation task

Implement the Fedora-specific safe session path in `engine.go`, then build a complete installer binary from an upstream checkout and run its tests. Only after that should the first Fedora VM test be attempted.
