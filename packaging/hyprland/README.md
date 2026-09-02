# Ryoku Hyprland stack for Fedora

This directory is the packaging workstream for the compositor ABI owned by
Ryoku-on-Fedora.

## Pin

- Hyprland: `v0.56.2`
- Upstream release date: 2026-08-05
- Upstream source asset SHA-256:
  `03ad3f5ef152ff44116ffd56fcf808486211ecabf4f0ba567108ee746ba5cd2e`

Ryoku uses native Hyprland Lua configuration and therefore requires the 0.55+
generation. We pin an exact compositor release rather than following git HEAD.

## Architecture

Fedora remains responsible for normal system libraries, the kernel, Mesa,
drivers and SELinux. Hyprland-specific libraries whose ABI moves with Hyprland
are built at fixed versions and installed under a private Ryoku prefix.

Planned RPM split:

- `ryoku-hyprland` — compositor, `Hyprland`, `hyprctl`, session/data
- `ryoku-hyprland-devel` — Hyprland headers + pkg-config metadata for plugins
- `ryoku-xdg-desktop-portal-hyprland` — ABI-matched portal integration
- `ryoku-hyprland-plugins` — Ryoku's ABI-matched plugin set

The compositor RPM will provide the generic `hyprland` RPM capability so the
rest of the port can depend on the role rather than a third-party COPR package.

## Why a private dependency prefix

Fedora 44 does not carry a complete current Hyprland compositor stack. Hyprland
0.56.x also moves faster than Fedora's Hypr-specific libraries. Installing
newer libhypr* builds into the global Fedora library namespace can break other
packages. Ryoku will instead keep its pinned copies under a private directory
and use build-time RPATH for the compositor and ABI-linked helpers.

This mirrors the key invariant used by the official Ryoku-on-NixOS port:
Ryoku owns the compositor ABI rather than inheriting an arbitrary host version.

## Reference packaging

During the Fedora audit we examined Asher Buk's MIT-licensed
`AshBuk/Hyprland-Fedora` packaging. It demonstrates the same private-prefix
approach on Fedora 43/44 and is a useful compatibility reference. Ryoku's RPMs
will retain attribution where implementation is derived from that work and
will use Ryoku-owned sources/build assets.

## Current gate

Before writing the production spec, CI probes Hyprland's official
`source-v0.56.2.tar.gz` release asset to determine which subprojects are
already present. We prefer the official release archive over depending on
another COPR maintainer's release mirrors.
