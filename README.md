# Ryoku on Fedora

Fedora port of [Ryoku](https://github.com/neur0map/ryoku-arch), developed against Fedora 44 first and designed for Fedora 45 compatibility.

The port is intentionally an **additive desktop layer**, not an Arch-to-Fedora distro transplant. Fedora remains responsible for its kernel, bootloader, dracut/initramfs, SELinux, graphics-driver policy, PAM, display manager, NetworkManager policy, RPM/DNF database, and release upgrades.

## Audited upstream baseline

- Upstream: `neur0map/ryoku-arch`
- Branch audited: `unstable-dev`
- Version: `0.53.7-beta.19`
- Commit: `85cd1cbd1f9cd90f72283fbad9094772156ec4f3`
- Primary development target: Fedora 44 x86_64
- Compatibility target: Fedora 45

The Phase 1 overlay refuses to patch any other upstream commit. Moving the pin requires a fresh compatibility audit.

## Phase 1 status

The `phase1-safe-session` branch now has a host-preserving Fedora integration path.

Already validated in Fedora 44 CI:

- Fedora distro detection and DNF/RPM package backend
- fail-closed Arch → Fedora package mapping
- every currently mapped Fedora package resolves from Fedora 44 repositories
- upstream Ryoku installer tests pass after applying the Fedora overlay
- integrated Fedora installer builds successfully
- Fedora dry-run smoke plan passes
- Ryoku shell daemon, Hub, Rashin and CLI compile natively on Fedora 44
- `Ryoku.Blobs` builds against Fedora Qt 6 and has no unresolved ELF dependencies
- Fedora-safe source deploy blocks Arch boot/network/package-manager mutations
- source RPM inputs and `%prep` for the pinned Hyprland/portal stack validate on Fedora 44
- RPM specs and BuildRequires validate on Fedora 44
- VM host-preservation harness is present for the first destructive login test

The current work item is the Ryoku-owned **Hyprland 0.56.2 + xdg-desktop-portal-hyprland 1.4.1 RPM stack**. Full binary RPM build/linkage validation must pass before a clean Fedora 44 VM install is considered reproducible.

## Host-preservation contract

Phase 1 must not:

- replace Fedora's kernel
- invoke `mkinitcpio` or install Limine
- rewrite Fedora's existing PAM configuration
- disable SELinux
- switch GDM/KDE's display manager to SDDM
- force NetworkManager to the iwd backend
- install Arch GPU-driver policy
- run `pacman`, `yay`, or `makepkg` on the Fedora host
- remove the existing Fedora desktop or unrelated packages

The one intentional system-level desktop addition is:

```text
/usr/share/wayland-sessions/ryoku.desktop
```

Everything else in the initial source deployment is kept user-scoped wherever possible.

## Fedora safety guards

Until Fedora-native system-management backends exist, the deployed Ryoku CLI blocks upstream commands whose implementations currently assume Arch policy, including:

`update`, `doctor`, `recovery`, `rollback`, `snapshots`, `track`, `deploy`, `security-key`, and `keyboard`.

Fedora continues to update through DNF during this phase.

## Repository layout

- `prototype/` — Fedora distro adapter, package map and read-only preflight
- `overlay/ryoku-shell-installer/` — Fedora-specific installer/runtime integration
- `scripts/apply-fedora-overlay.py` — fail-closed overlay applicator
- `scripts/build-fedora-installer.sh` — reproducible integrated installer builder
- `scripts/list-fedora-packages.py` — package-map extraction used by CI
- `packaging/hyprland/` — pinned Ryoku Hyprland/portal RPM stack
- `tests/vm/` — before/after Fedora host-preservation checks
- `docs/PORTING_AUDIT.md` — Phase 0 compatibility audit
- `docs/PHASE1_VM_VALIDATION.md` — Fedora 44 destructive VM acceptance procedure

## Local integrated-installer build

With Git, Python 3 and Go installed:

```bash
bash scripts/build-fedora-installer.sh
```

The builder fetches only the pinned upstream commit, applies the Fedora overlay, runs the integrated installer tests, and emits the binary plus SHA-256 checksum under `dist/`.

Do **not** run the Phase 1 installer on a daily-use Fedora machine yet. The first destructive target remains a disposable Fedora 44 VM after the Ryoku-owned compositor RPM stack is green.
