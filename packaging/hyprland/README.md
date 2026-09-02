# Ryoku Hyprland RPM stack

This directory is the Fedora compositor layer for Ryoku-on-Fedora.

## Phase 1 pins

- Hyprland: 0.56.2
- xdg-desktop-portal-hyprland: 1.4.1
- Hyprland protocols: 0.7.0
- hyprwayland-scanner: 0.4.6
- hyprutils: 0.14.0
- hyprlang: 0.6.8
- hyprcursor: 0.1.13
- hyprgraphics: 0.5.1
- aquamarine: 0.14.0
- hyprwire: 0.3.1
- Lua: 5.5.0

Fedora 44 does not ship a current Hyprland compositor, and Hyprland 0.55+
requires the Lua-era stack Ryoku's hyprland.lua uses. The specs therefore use
a hermetic, pinned vendor prefix instead of replacing Fedora's independently
packaged hypr* libraries.

## Package identity

- ryoku-hyprland provides/conflicts with hyprland and hyprland-devel.
- ryoku-xdg-desktop-portal-hyprland provides/conflicts with
  xdg-desktop-portal-hyprland.
- The private compositor ABI lives under
  /usr/libexec/ryoku-hyprland/vendor/.

This is not yet a production COPR. CI must first validate the specs on Fedora
44, then the resulting RPMs must pass a Fedora 44 VM login/session test.
