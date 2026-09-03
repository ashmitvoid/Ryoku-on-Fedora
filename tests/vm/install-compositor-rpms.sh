#!/usr/bin/env bash
# Install only the Ryoku compositor + portal RPMs into a disposable Fedora VM.
# hyprlock/hypridle companion RPMs are deliberately not installed in Phase 1.
set -euo pipefail

dir="${1:?usage: install-compositor-rpms.sh /path/to/extracted-rpm-artifact}"
[[ -d "$dir" ]] || { echo "not a directory: $dir" >&2; exit 2; }

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
else
  echo "/etc/os-release is missing" >&2
  exit 2
fi
[[ ${ID:-} == fedora && ${VERSION_ID:-} == 44 ]] || {
  echo "Phase 1 VM compositor install currently targets Fedora 44 only" >&2
  exit 2
}

if command -v getenforce >/dev/null 2>&1 && [[ $(getenforce) != Enforcing ]]; then
  echo "SELinux must be Enforcing for the validation install" >&2
  exit 2
fi

mapfile -t hypr_candidates < <(
  find "$dir" -type f -name 'ryoku-hyprland-[0-9]*.x86_64.rpm' | sort
)
mapfile -t portal_candidates < <(
  find "$dir" -type f -name 'ryoku-xdg-desktop-portal-hyprland-[0-9]*.x86_64.rpm' | sort
)

(( ${#hypr_candidates[@]} == 1 )) || {
  printf 'expected exactly one ryoku-hyprland x86_64 RPM, found %d\n' "${#hypr_candidates[@]}" >&2
  printf '%s\n' "${hypr_candidates[@]-}" >&2
  exit 2
}
(( ${#portal_candidates[@]} == 1 )) || {
  printf 'expected exactly one Ryoku portal x86_64 RPM, found %d\n' "${#portal_candidates[@]}" >&2
  printf '%s\n' "${portal_candidates[@]-}" >&2
  exit 2
}

hypr="${hypr_candidates[0]}"
portal="${portal_candidates[0]}"

# A clean Fedora M1 VM must not have some unrelated Hyprland package already
# owning the standard binaries. This keeps the result attributable to our RPM.
if rpm -q hyprland >/dev/null 2>&1; then
  echo "a non-Ryoku hyprland package is already installed; use a clean Fedora VM" >&2
  exit 2
fi

echo "==> Installing Ryoku compositor stack"
echo "    $hypr"
echo "    $portal"
sudo dnf -y install --setopt=install_weak_deps=False "$hypr" "$portal"

rpm -q ryoku-hyprland
rpm -q ryoku-xdg-desktop-portal-hyprland

# qylock is Ryoku's M1 locker. Pulling hyprlock here would add a PAM service and
# invalidate the host-preservation contract.
if rpm -q hyprlock >/dev/null 2>&1; then
  echo "hyprlock was unexpectedly installed; refusing this M1 validation state" >&2
  exit 1
fi

command -v Hyprland >/dev/null 2>&1
command -v hyprctl >/dev/null 2>&1
test -x /usr/libexec/xdg-desktop-portal-hyprland

if command -v getenforce >/dev/null 2>&1; then
  [[ $(getenforce) == Enforcing ]] || {
    echo "SELinux changed away from Enforcing during RPM installation" >&2
    exit 1
  }
fi

echo "Ryoku Fedora compositor RPMs installed with host policy preserved."
