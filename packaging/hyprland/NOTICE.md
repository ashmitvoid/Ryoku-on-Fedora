# Hyprland Fedora packaging provenance

The RPM specifications in this directory are downstream derivatives of:

- Project: AshBuk/Hyprland-Fedora
- Source commit: 07efaa0d125d2ec2cc082e462e87f7bdcae354db
- Original author: Asher Buk
- Original spec/script license: MIT
- Upstream project: https://github.com/AshBuk/Hyprland-Fedora

Ryoku-on-Fedora modifications namespace the compositor and portal RPMs, keep
the vendored ABI under /usr/libexec/ryoku-hyprland/vendor/, and pin the stack
for the Ryoku Fedora support matrix.

The runtime software built by these specs retains each upstream project's own
license; the MIT notice applies to the packaging specifications and scripts.
