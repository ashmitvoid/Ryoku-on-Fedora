# Ryoku on Fedora

Fedora porting work for [Ryoku](https://github.com/neur0map/ryoku-arch), targeting Fedora 44 first and Fedora 45 compatibility next.

This repository currently contains the Phase 0 audit and the first Fedora installer prototype. The initial milestone is intentionally conservative: preserve Fedora ownership of the kernel, bootloader, SELinux, graphics stack, PAM, display manager, and networking policy while bringing up a selectable Ryoku session.

## Current baseline

- Upstream: `neur0map/ryoku-arch`
- Branch: `unstable-dev`
- Version audited: `0.53.7-beta.19`
- Commit: `85cd1cbd1f9cd90f72283fbad9094772156ec4f3`
- Primary development target: Fedora 44 x86_64
- Compatibility target: Fedora 45

## Repository layout

- `prototype/` — Fedora-aware installer scaffold and tests
- `docs/PORTING_AUDIT.md` — Phase 0 compatibility/audit ledger
- `TEST-RESULTS.txt` — initial local test results

## Safety policy for the Fedora port

The prototype must not transplant Arch-specific system ownership onto Fedora. In particular, the first milestone does **not** replace Fedora's bootloader or initramfs tooling, disable SELinux, replace Fedora's kernel/driver stack, rewrite PAM, or force-switch the display manager/network stack.

## Status

Phase 0 is in progress. The next milestone is a Fedora-specific safe session path followed by Fedora 44 VM validation.
