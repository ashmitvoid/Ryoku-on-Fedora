#!/usr/bin/env bash
# Capture the Fedora-owned state that Ryoku-on-Fedora M1 promises not to change.
# Usage: capture-fedora-host-state.sh <output>
set -euo pipefail

out="${1:?usage: capture-fedora-host-state.sh <output>}"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
trap 'rc=$?; printf "capture-fedora-host-state: failed at line %d (exit %d)\n" "$LINENO" "$rc" >&2; exit "$rc"' ERR

value() {
  local key="$1"; shift
  local text rc=0
  if text="$("$@" 2>/dev/null)"; then
    rc=0
  else
    rc=$?
  fi
  text="$(printf '%s' "$text" | tr '\n' ' ' | sed -E 's/[[:space:]]+$//')"
  if [[ -z "$text" && $rc -ne 0 ]]; then
    text="status:$rc"
  fi
  printf '%s=%s\n' "$key" "$text"
}

hash_path() {
  local key="$1" path="$2"
  local digest

  if [[ ! -e "$path" && ! -L "$path" ]]; then
    printf '%s=absent\n' "$key"
    return 0
  fi

  if [[ -L "$path" ]]; then
    printf '%s=symlink:%s\n' "$key" "$(readlink "$path")"
    return 0
  fi

  if [[ -d "$path" ]]; then
    # Fedora keeps parts of /boot and some policy directories root-readable
    # only. Hash them through sudo without mutating anything.
    if digest="$(
      sudo find "$path" -xdev -type f -exec sha256sum {} + 2>/dev/null |
        LC_ALL=C sort |
        sha256sum |
        awk '{print $1}'
    )"; then
      printf '%s=%s\n' "$key" "$digest"
    else
      return $?
    fi
    return 0
  fi

  if [[ -r "$path" ]]; then
    digest="$(sha256sum "$path" | awk '{print $1}')"
  else
    digest="$(sudo sha256sum "$path" | awk '{print $1}')"
  fi
  printf '%s=%s\n' "$key" "$digest"
}

{
  echo 'format=ryoku-fedora-host-state-v1'

  if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    printf 'os_id=%s\n' "${ID:-}"
    printf 'os_version=%s\n' "${VERSION_ID:-}"
  fi

  value kernel_running uname -r
  printf 'kernel_packages='
  rpm -qa 'kernel*' 2>/dev/null | sort | tr '\n' ' ' | sed -E 's/[[:space:]]+$//'
  printf '\n'
  value selinux_mode getenforce
  value selinux_config grep -E '^[[:space:]]*SELINUX=' /etc/selinux/config
  value default_target systemctl get-default

  printf 'display_manager='
  if [[ -L /etc/systemd/system/display-manager.service ]]; then
    readlink /etc/systemd/system/display-manager.service
  else
    dm_status="$(systemctl status display-manager.service --no-pager 2>/dev/null || true)"
    printf '%s\n' "$dm_status" |
      sed -n 's/.*Loaded: loaded (\([^;]*\).*/\1/p' | head -n1
  fi

  value gdm_enabled systemctl is-enabled gdm.service
  value sddm_enabled systemctl is-enabled sddm.service
  value networkmanager_enabled systemctl is-enabled NetworkManager.service

  hash_path pam_dir /etc/pam.d
  hash_path networkmanager_conf /etc/NetworkManager
  hash_path selinux_config_file /etc/selinux/config
  hash_path grub_defaults /etc/default/grub
  hash_path grub_efi /boot/efi/EFI/fedora
  hash_path loader_entries /boot/loader/entries

  # We deliberately do not require this to be absent before install. If a
  # previous Ryoku-on-Fedora run owns it, the verifier checks its marker later.
  if [[ -f /usr/share/wayland-sessions/ryoku.desktop ]]; then
    printf 'ryoku_session_before=present\n'
  else
    printf 'ryoku_session_before=absent\n'
  fi
} > "$tmp"

mv -f "$tmp" "$out"
printf 'captured Fedora host state -> %s\n' "$out"
