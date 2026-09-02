#!/usr/bin/env bash
# Remove the Phase 1 Ryoku-on-Fedora test install from a disposable Fedora 44 VM.
# Run this from GNOME/GDM fallback, never from a live Ryoku/Hyprland session.
set -euo pipefail

before="${1:?usage: remove-phase1.sh /path/to/before.state}"

if [[ -n ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
  echo "refusing to remove Ryoku from inside a running Hyprland session" >&2
  exit 2
fi

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
fi
[[ ${ID:-} == fedora && ${VERSION_ID:-} == 44 ]] || {
  echo "Phase 1 removal validation currently targets Fedora 44 only" >&2
  exit 2
}

state_root="$HOME/.local/state/ryoku/shell-install"
mapfile -t backups < <(find "$state_root" -maxdepth 1 -mindepth 1 -type d -name 'backup-*' -print 2>/dev/null | sort)
(( ${#backups[@]} > 0 )) || {
  echo "no Ryoku shell-install backup was found under $state_root" >&2
  exit 2
}
backup="${backups[${#backups[@]}-1]}"
restore="$backup/restore.sh"
[[ -x "$restore" ]] || {
  echo "restore script is missing or not executable: $restore" >&2
  exit 2
}

echo "==> Stopping Ryoku user services"
systemctl --user disable --now ryoku-ai-usage.timer 2>/dev/null || true
systemctl --user stop ryoku-shell.service ryogami.service ryoku-rashin.service 2>/dev/null || true

echo "==> Restoring pre-Ryoku user configuration"
bash "$restore"

# If a path did not exist before installation, upstream's restore script has no
# line for it. Remove only the Ryoku-created copy in that case.
restore_or_remove_dir() {
  local rel="$1"
  if [[ ! -e "$backup/$rel" && ! -L "$backup/$rel" ]]; then
    rm -rf "$HOME/$rel"
  fi
}

restore_or_remove_dir ".config/hypr"
restore_or_remove_dir ".config/quickshell"
restore_or_remove_dir ".config/matugen"
restore_or_remove_dir ".local/share/quickshell-lockscreen"
restore_or_remove_dir ".local/share/qylock"

# Fedora host-preserving mode intentionally creates these Ryoku-only paths.
rm -rf   "$HOME/.config/ryoku-terminal"   "$HOME/.config/hyprland-preview-share-picker"   "$HOME/.local/share/ryogami"

# If the user had no systemd-user tree before the install, remove Ryoku units
# individually rather than deleting the directory wholesale.
if [[ ! -e "$backup/.config/systemd/user" ]]; then
  rm -f     "$HOME/.config/systemd/user"/ryoku-*.service     "$HOME/.config/systemd/user"/ryoku-*.timer     "$HOME/.config/systemd/user"/ryogami.service
fi

payload="$HOME/.cache/ryoku-shell-install/repo"
bindir="$HOME/.local/bin"
appshare="${XDG_DATA_HOME:-$HOME/.local/share}"

echo "==> Removing Ryoku-owned user binaries and launchers"
rm -f   "$bindir/ryoku"   "$bindir/ryoku.real"   "$bindir/ryoku-shell"   "$bindir/ryoku-reload-cover"   "$bindir/ryoku-depth"   "$bindir/ryogami"   "$bindir/ryoku-hub"   "$bindir/ryoku-rashin"   "$bindir/ryoku-plugins-place"   "$bindir/ryoku-fastfetch"   "$bindir/ryotunes"

if [[ -L "$bindir/rashin" ]] && [[ $(readlink "$bindir/rashin") == ryoku-rashin ]]; then
  rm -f "$bindir/rashin"
fi

# The cached pinned payload is the source of truth for first-party app helpers,
# desktop entries and icon names. Remove only names shipped by that payload.
if [[ -d "$payload/ryoku/apps" ]]; then
  for appdir in "$payload"/ryoku/apps/*/; do
    [[ -d "$appdir" ]] || continue
    appname="$(basename "$appdir")"

    for b in "$appdir"bin/*; do
      [[ -f "$b" ]] && rm -f "$bindir/$(basename "$b")"
    done

    for gomod in "$appdir"*/go.mod; do
      [[ -f "$gomod" ]] || continue
      helper="$(sed -n -E 's/^module[[:space:]]+//p' "$gomod" | head -1)"
      [[ -n "$helper" ]] && rm -f "$bindir/$helper"
    done

    for desktop in "$appdir"*.desktop; do
      [[ -f "$desktop" ]] && rm -f "$appshare/applications/$(basename "$desktop")"
    done

    if [[ -d "$appdir/quickshell" ]]; then
      rm -f "$appshare/icons/hicolor/scalable/apps/$appname.svg"
    fi
  done
fi

rm -f   "$appshare/applications/ryoku-hub.desktop"   "$appshare/icons/hicolor/scalable/apps/ryoku-hub.svg"   "$appshare/applications/ryotunes.desktop"   "$appshare/icons/hicolor/scalable/apps/ryotunes.svg"

systemctl --user daemon-reload 2>/dev/null || true

# restore.sh normally removes this. Keep a marker-guarded fallback so an
# interrupted restore cannot leave a stale login entry, while never deleting a
# session file owned by something else.
session=/usr/share/wayland-sessions/ryoku.desktop
if [[ -f "$session" ]]; then
  if grep -q '^X-Ryoku-Fedora-Port=true$' "$session"; then
    sudo rm -f "$session"
  else
    echo "refusing to delete unowned $session" >&2
    exit 1
  fi
fi

echo "==> Removing only Ryoku compositor RPMs"
if rpm -q ryoku-xdg-desktop-portal-hyprland >/dev/null 2>&1; then
  sudo rpm -e ryoku-xdg-desktop-portal-hyprland
fi
if rpm -q ryoku-hyprland >/dev/null 2>&1; then
  sudo rpm -e ryoku-hyprland
fi

if rpm -q ryoku-hyprland >/dev/null 2>&1 ||
   rpm -q ryoku-xdg-desktop-portal-hyprland >/dev/null 2>&1; then
  echo "Ryoku compositor RPM removal did not complete" >&2
  exit 1
fi

echo "==> Re-checking Fedora-owned state"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$here/verify-fedora-host-preserved.sh" "$before"

echo "Phase 1 Ryoku removal completed and Fedora host preservation passed."
