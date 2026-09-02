#!/usr/bin/env bash
# Build the Phase 1 Fedora installer from the exact audited Ryoku upstream.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pin="85cd1cbd1f9cd90f72283fbad9094772156ec4f3"
out="${1:-$root/dist/ryoku-shell-install-fedora44-phase1}"

for cmd in git python3 go sha256sum; do
  command -v "$cmd" >/dev/null 2>&1 || {
    printf 'build-fedora-installer: %s is required\n' "$cmd" >&2
    exit 1
  }
done

mkdir -p "$(dirname "$out")"
out_dir="$(cd "$(dirname "$out")" && pwd)"
out="$out_dir/$(basename "$out")"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "==> Fetching pinned Ryoku upstream $pin"
git init -q "$work/upstream"
git -C "$work/upstream" remote add origin https://github.com/neur0map/ryoku-arch.git
git -C "$work/upstream" fetch -q --depth=1 origin "$pin"
git -C "$work/upstream" checkout -q --detach FETCH_HEAD
test "$(git -C "$work/upstream" rev-parse HEAD)" = "$pin"

echo "==> Applying Fedora host-preserving overlay"
python3 "$root/scripts/apply-fedora-overlay.py" "$work/upstream"

echo "==> Testing integrated installer"
(
  cd "$work/upstream/ryoku-shell-installer"
  gofmt -w distro.go fedora.go engine.go main.go distro_test.go fedora_test.go
  go test ./...
)

echo "==> Building integrated installer"
tmpout="$out.tmp"
(
  cd "$work/upstream/ryoku-shell-installer"
  go build -trimpath -o "$tmpout" .
)
chmod 0755 "$tmpout"
mv -f "$tmpout" "$out"
sha256sum "$out" > "$out.sha256"

printf 'built: %s\n' "$out"
printf 'sha256: %s\n' "$out.sha256"
