#!/usr/bin/env bash
# Fedora-aware prototype of ryoku-shell-installer/install.sh.
# Baseline: neur0map/ryoku-arch unstable-dev 0.53.7-beta.19.
set -euo pipefail

main() {
  local ref="${RYOKU_SHELL_REF:-unstable-dev}"
  local raw="https://raw.githubusercontent.com/neur0map/ryoku-arch/${ref}/ryoku-shell-installer"

  say() { printf '\033[38;2;242;86;35m==>\033[0m %s\n' "$*"; }
  die() { printf 'ryoku-shell: %s\n' "$*" >&2; exit 1; }

  [[ $(id -u) -ne 0 ]] || die "run as your normal user, not root (sudo is used when needed)"
  [[ ! -e /etc/NIXOS ]] || die "NixOS uses the official Ryoku-on-NixOS port"

  local ryoku_family
  if command -v pacman >/dev/null 2>&1; then
    ryoku_family=arch
  elif command -v apt-get >/dev/null 2>&1; then
    ryoku_family=debian
  elif command -v dnf >/dev/null 2>&1; then
    ryoku_family=fedora
  else
    die "unsupported distribution: expected pacman, apt-get, or dnf"
  fi

  [[ $(uname -m) == x86_64 ]] || die "Ryoku currently targets x86_64 only"
  [[ -d /run/systemd/system ]] || die "this installer needs systemd"
  command -v curl >/dev/null 2>&1 || die "curl is required"

  if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    case "${ID:-} ${ID_LIKE:-}" in
      *arch*|*debian*|*fedora*) ;;
      *) say "warning: ${PRETTY_NAME:-unknown distro} is not recognised; continuing as ${ryoku_family}" ;;
    esac

    if [[ $ryoku_family == fedora ]]; then
      [[ ${ID:-} == fedora || " ${ID_LIKE:-} " == *" fedora "* ]] \
        || say "warning: Fedora-family derivative detected; initial support is tested against Fedora itself"
      case "${VERSION_ID:-}" in
        44) say "Fedora 44 detected: Ryoku Fedora bootstrap path" ;;
        45) say "Fedora 45 detected: compatibility target (pre-release until Fedora 45 final)" ;;
        *) say "warning: Fedora ${VERSION_ID:-unknown} is outside the initial 44/45 support window" ;;
      esac
    fi
  fi

  case "$ryoku_family" in
    debian) say "Debian detected: desktop components are built from source" ;;
    fedora) say "Fedora detected: desktop components are built from source; Fedora keeps ownership of kernel, bootloader and SELinux" ;;
  esac

  local work
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT

  say "fetching the Ryoku shell installer (${ref})"
  curl -fsSL --retry 3 -o "$work/ryoku-shell-install" "$raw/ryoku-shell-install"
  curl -fsSL --retry 3 -o "$work/ryoku-shell-install.sha256" "$raw/ryoku-shell-install.sha256"
  (cd "$work" && sha256sum --check --quiet ryoku-shell-install.sha256) \
    || die "checksum mismatch on the downloaded installer; try again"
  chmod +x "$work/ryoku-shell-install"

  if [[ $ryoku_family == fedora ]]; then
    die "Fedora detection is wired, but upstream's prebuilt installer binary does not contain the Fedora adapter yet. Build the prototype installer from the patch branch before running the mutation phase."
  fi

  say "starting the installer"
  local rc=0
  if [[ ! -t 0 && -r /dev/tty ]]; then
    RYOKU_SHELL_REF="$ref" "$work/ryoku-shell-install" "$@" </dev/tty || rc=$?
  else
    RYOKU_SHELL_REF="$ref" "$work/ryoku-shell-install" "$@" || rc=$?
  fi
  return "$rc"
}

main "$@"
