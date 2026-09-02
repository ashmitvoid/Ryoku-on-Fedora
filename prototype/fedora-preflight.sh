#!/usr/bin/env bash
# Read-only Fedora readiness probe for the Ryoku port.
set -euo pipefail

ok=0
warn=0
fail=0

say()  { printf '[INFO] %s\n' "$*"; }
pass() { printf '[ OK ] %s\n' "$*"; ok=$((ok+1)); }
nope() { printf '[FAIL] %s\n' "$*"; fail=$((fail+1)); }
note() { printf '[WARN] %s\n' "$*"; warn=$((warn+1)); }

[[ -r /etc/os-release ]] || { nope '/etc/os-release missing'; exit 1; }
# shellcheck source=/dev/null
. /etc/os-release

if [[ ${ID:-} == fedora ]]; then
  pass "Fedora detected (${PRETTY_NAME:-Fedora})"
elif [[ " ${ID_LIKE:-} " == *" fedora "* ]]; then
  note "Fedora-family derivative detected (${PRETTY_NAME:-unknown}); initial validation targets Fedora itself"
else
  nope "not a Fedora-family host (${PRETTY_NAME:-unknown})"
fi

case "${VERSION_ID:-}" in
  44) pass 'Fedora 44 is the current development baseline' ;;
  45) note 'Fedora 45 compatibility target detected; treat as pre-release until Fedora 45 final' ;;
  *) note "Fedora ${VERSION_ID:-unknown} is outside the initial 44/45 matrix" ;;
esac

[[ $(uname -m) == x86_64 ]] && pass 'x86_64 architecture' || nope "unsupported architecture: $(uname -m)"
[[ -d /run/systemd/system ]] && pass 'systemd is running' || nope 'systemd runtime not detected'
command -v dnf >/dev/null 2>&1 && pass 'dnf available' || nope 'dnf missing'
command -v rpm >/dev/null 2>&1 && pass 'rpm available' || nope 'rpm missing'

if command -v getenforce >/dev/null 2>&1; then
  selinux=$(getenforce 2>/dev/null || true)
  case "$selinux" in
    Enforcing) pass 'SELinux is Enforcing (this is the intended state; the port must work with it)' ;;
    Permissive) note 'SELinux is Permissive; do not use this to hide labeling/policy bugs' ;;
    Disabled) note 'SELinux is Disabled; Fedora validation should also be performed with Enforcing' ;;
    *) note "SELinux state: ${selinux:-unknown}" ;;
  esac
fi

# Packages that are already known to exist in Fedora 44's official repositories
# and are central to the source-build path.
critical_pkgs=(
  quickshell
  qt6-qtbase-devel
  qt6-qtdeclarative-devel
  qt6-qtmultimedia-devel
  qt6-qtshadertools-devel
  qt6-qtsvg-devel
  qt6-qt5compat-devel
  NetworkManager
  pipewire
  wireplumber
  selinux-policy
)

if command -v dnf >/dev/null 2>&1; then
  say 'Checking critical Fedora packages (read-only repoquery)'
  for p in "${critical_pkgs[@]}"; do
    if dnf -q repoquery --available "$p" 2>/dev/null | grep -q . || rpm -q "$p" >/dev/null 2>&1; then
      pass "package available: $p"
    else
      nope "package unavailable: $p"
    fi
  done
fi

# The first source-port milestone deliberately requires Hyprland to exist before
# the installer mutates anything. The production port will replace this with a
# Ryoku-owned RPM/COPR compositor stack so plugin ABI stays deterministic.
if command -v Hyprland >/dev/null 2>&1; then
  pass "Hyprland present: $(Hyprland --version 2>/dev/null | head -n1 || printf unknown)"
else
  nope 'Hyprland is not installed; Phase 1 currently treats this as a blocker until the Ryoku-owned Fedora Hyprland RPM/COPR stack is ready'
fi

if command -v qs >/dev/null 2>&1; then
  pass 'Quickshell executable (qs) present'
else
  note 'Quickshell is not installed yet; Fedora 44 packages it officially and the installer can add it'
fi

if pkg-config --exists hyprland 2>/dev/null; then
  pass "Hyprland development metadata present ($(pkg-config --modversion hyprland))"
else
  note 'Hyprland pkg-config metadata absent; Ryoku compositor plugins will remain disabled in the source prototype'
fi

if rpm -q xdg-desktop-portal-hyprland >/dev/null 2>&1; then
  pass 'xdg-desktop-portal-hyprland installed'
else
  note 'xdg-desktop-portal-hyprland not installed; screen sharing/file portal integration is a Phase 2/COPR item'
fi

printf '\nSummary: %d ok, %d warning(s), %d blocker(s)\n' "$ok" "$warn" "$fail"
(( fail == 0 ))
