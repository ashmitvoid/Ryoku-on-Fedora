#!/usr/bin/env bash
# Compare a pre-install Fedora snapshot with the current machine.
# Only Ryoku's own session/config additions may differ.
# Usage: verify-fedora-host-preserved.sh <before-state>
set -euo pipefail

before="${1:?usage: verify-fedora-host-preserved.sh <before-state> [--removed]}"
mode="${2:-installed}"
case "$mode" in
  installed) ;;
  --removed) mode=removed ;;
  *) echo "unknown verification mode: $mode" >&2; exit 2 ;;
esac
[[ -r "$before" ]] || { echo "missing state file: $before" >&2; exit 2; }

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
after="$(mktemp)"
trap 'rm -f "$after"' EXIT
"$here/capture-fedora-host-state.sh" "$after" >/dev/null

declare -A old now
while IFS='=' read -r k v; do old["$k"]="$v"; done < "$before"
while IFS='=' read -r k v; do now["$k"]="$v"; done < "$after"

fails=0
check_same() {
  local key="$1" label="$2"
  if [[ "${old[$key]-}" == "${now[$key]-}" ]]; then
    printf '[ OK ] %s\n' "$label"
  else
    printf '[FAIL] %s changed\n       before: %s\n       after:  %s\n'       "$label" "${old[$key]-<missing>}" "${now[$key]-<missing>}"
    fails=$((fails+1))
  fi
}

check_same kernel_running 'running Fedora kernel'
check_same kernel_packages 'installed kernel package set'
check_same selinux_mode 'SELinux enforcement mode'
check_same selinux_config 'SELinux configured mode'
check_same default_target 'systemd default target'
check_same display_manager 'display manager selection'
check_same gdm_enabled 'GDM enablement'
check_same sddm_enabled 'SDDM enablement'
check_same networkmanager_enabled 'NetworkManager enablement'
check_same pam_dir '/etc/pam.d contents'
check_same networkmanager_conf '/etc/NetworkManager policy'
check_same selinux_config_file '/etc/selinux/config'
check_same grub_defaults '/etc/default/grub'
check_same grub_efi 'Fedora EFI boot files'
check_same loader_entries 'boot loader entries'

session=/usr/share/wayland-sessions/ryoku.desktop
if [[ "$mode" == installed ]]; then
  if [[ -f "$session" ]] && grep -q '^X-Ryoku-Fedora-Port=true
if command -v getenforce >/dev/null 2>&1 && [[ $(getenforce) != Enforcing ]]; then
  printf '[FAIL] SELinux is not Enforcing after installation\n'
  fails=$((fails+1))
else
  printf '[ OK ] SELinux remains Enforcing\n'
fi

if (( fails )); then
  printf '\n%d Fedora host-preservation check(s) failed.\n' "$fails" >&2
  exit 1
fi
printf '\nFedora host-preservation contract passed.\n'
 "$session"; then
    printf '[ OK ] Ryoku Wayland session is registered and owned by this port\n'
  else
    printf '[FAIL] managed Ryoku Wayland session is missing or lacks its ownership marker\n'
    fails=$((fails+1))
  fi
else
  if [[ ! -e "$session" ]]; then
    printf '[ OK ] Ryoku Wayland session was removed\n'
  else
    printf '[FAIL] Ryoku Wayland session still exists after removal\n'
    fails=$((fails+1))
  fi
fi

if command -v getenforce >/dev/null 2>&1 && [[ $(getenforce) != Enforcing ]]; then
  printf '[FAIL] SELinux is not Enforcing after installation\n'
  fails=$((fails+1))
else
  printf '[ OK ] SELinux remains Enforcing\n'
fi

if (( fails )); then
  printf '\n%d Fedora host-preservation check(s) failed.\n' "$fails" >&2
  exit 1
fi
printf '\nFedora host-preservation contract passed.\n'
