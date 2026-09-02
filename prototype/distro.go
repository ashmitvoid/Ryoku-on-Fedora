package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// distro is the only place the installer knows a package manager. Every step
// asks it for argv and for the local name of a package; nothing else branches on
// the distribution.
//
// fromSource distros have no [ryoku] repository, so the desktop is built from the
// cloned payload with ryoku/shell/deploy.sh instead of installed with pacman.
type distro struct {
	id         string
	name       string
	fromSource bool
	// strictRename makes the Arch-native base.packages manifest fail closed:
	// an unmapped package is skipped instead of being assumed to have the same
	// name. Fedora starts this way because feeding unknown Arch package names to
	// dnf would make the whole transaction fail. We can relax this as the map is
	// verified against Fedora repositories/COPR.
	strictRename bool

	// rename maps a base.packages (Arch) name to the local one. A missing key
	// means the name is identical unless strictRename is set; an empty value
	// means the package does not exist here and is skipped.
	rename map[string]string

	// build are the extra packages a fromSource install needs to compile the
	// Go programs, the Ryoku.Blobs QML plugin, and the Hyprland plugins.
	build []string

	installCmd []string
	removeCmd  []string
	updateCmd  []string
	refreshCmd []string
	queryCmd   []string
}

var archLinux = &distro{
	id:         "arch",
	name:       "Arch",
	installCmd: []string{"pacman", "-Syu", "--needed", "--noconfirm"},
	removeCmd:  []string{"pacman", "-R", "--noconfirm"},
	updateCmd:  []string{"pacman", "-Syu", "--noconfirm"},
	refreshCmd: []string{"pacman", "-Sy"},
	queryCmd:   []string{"pacman", "-Qq"},
}

// Package names verified against api.ftp-master.debian.org (testing/unstable).
var debianLinux = &distro{
	id:         "debian",
	name:       "Debian",
	fromSource: true,
	installCmd: []string{"apt-get", "-y", "install"},
	removeCmd:  []string{"apt-get", "-y", "remove"},
	updateCmd:  []string{"apt-get", "-y", "dist-upgrade"},
	refreshCmd: []string{"apt-get", "update"},
	queryCmd:   []string{"dpkg-query", "-W", "-f=${Status}"},
	build: []string{
		"build-essential", "cmake", "ninja-build", "pkgconf", "golang",
		"qt6-base-dev", "qt6-declarative-dev", "qt6-multimedia-dev",
		"qt6-shadertools-dev", "qt6-svg-dev", "qt6-5compat-dev", "qt6-wayland-dev",
		"hyprland-dev", "libhyprutils-dev",
	},
	rename: map[string]string{
		"base":                    "",
		"base-devel":              "build-essential",
		"bluez-utils":             "bluez",
		"edk2-ovmf":               "ovmf",
		"fd":                      "fd-find",
		"github-cli":              "gh",
		"gst-libav":               "gstreamer1.0-libav",
		"gst-plugins-bad":         "gstreamer1.0-plugins-bad",
		"gst-plugins-base":        "gstreamer1.0-plugins-base",
		"gst-plugins-good":        "gstreamer1.0-plugins-good",
		"gst-plugins-ugly":        "gstreamer1.0-plugins-ugly",
		"inter-font":              "fonts-inter",
		"linux-firmware":          "firmware-linux-free",
		"linux-headers":           "linux-headers-amd64",
		"networkmanager":          "network-manager",
		"noto-fonts":              "fonts-noto-core",
		"noto-fonts-cjk":          "fonts-noto-cjk",
		"noto-fonts-emoji":        "fonts-noto-color-emoji",
		"polkit":                  "polkitd",
		"python":                  "python3",
		"qemu-desktop":            "qemu-system-x86",
		"qt6-multimedia-ffmpeg":   "qt6-multimedia-dev",
		"rust":                    "rustc",
		"tesseract-data-eng":      "tesseract-ocr-eng",
		"ttf-firacode-nerd":       "fonts-firacode",
		"ttf-hack-nerd":           "fonts-hack",
		"ttf-jetbrains-mono-nerd": "fonts-jetbrains-mono",
		"vulkan-icd-loader":       "libvulkan1",
		"wpa_supplicant":          "wpasupplicant",
		"xorg-xwayland":           "xwayland",

		// Absent from Debian: skipped. matugen means no wallpaper palette,
		// the rest are optional tools and cosmetic extras.
		"limine":                        "",
		"limine-mkinitcpio-hook":        "",
		"limine-snapper-sync":           "",
		"mkinitcpio":                    "",
		"snap-pac":                      "",
		"matugen":                       "",
		"otf-space-grotesk":             "",
		"songrec":                       "",
		"spotify-launcher":              "",
		"ttf-material-symbols-variable": "",
		"vimix-cursors":                 "",
		"waifu2x-ncnn-vulkan":           "",
		"yazi":                          "",
	},
}

// Fedora 44 bootstrap map. This intentionally fails closed: only names we have
// verified or deliberately selected are sent to dnf. Missing optional pieces
// are listed in docs/PORTING_AUDIT.md and will move into the Ryoku COPR layer.
var fedoraLinux = &distro{
	id:           "fedora",
	name:         "Fedora",
	fromSource:   true,
	strictRename: true,
	installCmd:   []string{"dnf", "-y", "install"},
	removeCmd:    []string{"dnf", "-y", "remove"},
	updateCmd:    []string{"dnf", "-y", "upgrade", "--refresh"},
	refreshCmd:   []string{"dnf", "-y", "makecache"},
	queryCmd:     []string{"rpm", "-q"},
	build: []string{
		"gcc", "gcc-c++", "make", "cmake", "ninja-build", "pkgconf-pkg-config", "golang",
		"qt6-qtbase-devel", "qt6-qtdeclarative-devel", "qt6-qtmultimedia-devel",
		"qt6-qtshadertools-devel", "qt6-qtsvg-devel", "qt6-qt5compat-devel", "qt6-qtwayland-devel",
	},
	rename: map[string]string{
		// Installer bootstrap/toolchain. Fedora owns the base OS/kernel/boot
		// stack, so those Arch manifest entries are explicit no-ops here.
		"base":                    "",
		"base-devel":              "gcc",
		"rust":                    "rust",
		"linux":                   "",
		"linux-firmware":          "",
		"linux-headers":           "",
		"dkms":                    "",
		"mkinitcpio":              "",
		"sudo":                    "",
		"btrfs-progs":             "",
		"cryptsetup":              "",
		"dosfstools":              "",
		"efibootmgr":              "",
		"limine":                  "",
		"limine-mkinitcpio-hook":  "",
		"limine-snapper-sync":     "",
		"plymouth":                "",
		"snapper":                 "",
		"snap-pac":                "",

		// Core desktop services.
		"networkmanager":    "NetworkManager",
		"wpa_supplicant":    "wpa_supplicant",
		// Fedora networking policy stays host-owned for M1. Do not force Arch's
		// alternate backend/regulatory/firewall stack onto the host.
		"iwd":               "",
		"wireless-regdb":    "",
		"iw":                "",
		"nftables":          "",
		"bluez":             "bluez",
		"bluez-utils":       "bluez",
		"pipewire":          "pipewire",
		"pipewire-alsa":     "pipewire-alsa",
		"pipewire-pulse":    "pipewire-pulseaudio",
		"pipewire-audio":    "pipewire",
		"wireplumber":       "wireplumber",
		"alsa-utils":        "alsa-utils",
		"rtkit":             "rtkit",
		"mesa":              "mesa-dri-drivers",
		"vulkan-icd-loader": "vulkan-loader",

		// Wayland / Qt runtime. Hyprland itself and the ABI-locked plugin stack
		// are deliberately not sourced from an arbitrary third-party COPR here.
		"xorg-xwayland":          "xorg-x11-server-Xwayland",
		"xdg-desktop-portal-gtk": "xdg-desktop-portal-gtk",
		"xdg-user-dirs":          "xdg-user-dirs",
		"qt6-wayland":            "qt6-qtwayland",
		"qt5-wayland":            "qt5-qtwayland",
		"qt6ct":                  "qt6ct",
		"adwaita-icon-theme":     "adwaita-icon-theme",
		"gnome-themes-extra":     "",
		"papirus-icon-theme":     "papirus-icon-theme",
		"flatpak":                "flatpak",
		"sddm":                   "",
		"weston":                 "",
		"polkit":                 "polkit",
		"gnome-keyring":          "gnome-keyring",
		"qt6-declarative":        "qt6-qtdeclarative",
		"qt6-5compat":            "qt6-qt5compat",
		"qt6-svg":                "qt6-qtsvg",
		"qt6-multimedia":         "qt6-qtmultimedia",
		"qt6-multimedia-ffmpeg":  "qt6-qtmultimedia",
		"gst-plugins-base":       "gstreamer1-plugins-base",
		"gst-plugins-good":       "gstreamer1-plugins-good",
		"gst-plugins-bad":        "gstreamer1-plugins-bad-free",
		"gst-plugins-ugly":       "gstreamer1-plugins-ugly-free",
		"gst-libav":              "",
		"quickshell":             "quickshell",

		// Common runtime utilities already packaged by Fedora.
		"brightnessctl":         "brightnessctl",
		"upower":                "upower",
		"power-profiles-daemon": "power-profiles-daemon",
		"fuzzel":                "fuzzel",
		"grim":               "grim",
		"playerctl":          "playerctl",
		"slurp":              "slurp",
		"wl-clipboard":       "wl-clipboard",
		"chromium":           "chromium",
		"firefox":            "firefox",
		"kitty":              "kitty",
		"mpv":                "mpv",
		"nautilus":           "nautilus",
		"nautilus-python":    "nautilus-python",
		"qemu-desktop":       "qemu-kvm",
		"edk2-ovmf":          "edk2-ovmf",
		"virglrenderer":      "virglrenderer",
		"docker":             "",
		"gamescope":          "gamescope",
		"gamemode":           "gamemode",
		"mangohud":           "mangohud",
		"bash-completion":    "bash-completion",
		"bat":                "bat",
		"btop":               "btop",
		"fastfetch":          "fastfetch",
		"fd":                 "fd-find",
		"fish":               "fish",
		"fzf":                "fzf",
		"zsh":                "zsh",
		"zsh-autosuggestions":          "zsh-autosuggestions",
		"zsh-history-substring-search": "",
		"zsh-syntax-highlighting":      "zsh-syntax-highlighting",
		"git":                "git",
		"github-cli":         "gh",
		"neovim":             "neovim",
		"pciutils":           "pciutils",
		"ripgrep":            "ripgrep",
		"starship":           "",
		"zoxide":             "zoxide",
		"cava":               "cava",
		"cliphist":           "cliphist",
		"imagemagick":        "ImageMagick",
		"jq":                 "jq",
		"openrgb":            "openrgb",
		"ddcutil":            "ddcutil",
		"curl":               "curl",
		"libnotify":          "libnotify",
		"python":             "python3",
		"xdg-utils":          "xdg-utils",
		"ffmpeg":             "ffmpeg-free",
		"yt-dlp":             "yt-dlp",
		"desktop-file-utils": "desktop-file-utils",
		"libqalculate":       "libqalculate",
		"tesseract":          "tesseract",
		"tesseract-data-eng": "tesseract-langpack-eng",
		"zbar":               "zbar",
		"wf-recorder":        "wf-recorder",
		"wtype":              "wtype",

		// Developer extras.
		"go":          "golang",
		"nodejs":      "nodejs24",
		"npm":         "nodejs24-npm",
		"python-pip":  "python3-pip",
		"python-pipx": "pipx",
		"mise":        "",

		// CPU microcode is host-owned on Fedora and provided by microcode_ctl.
		"intel-ucode": "microcode_ctl",
		"amd-ucode":   "microcode_ctl",

		// Arch-only / not yet provided by Fedora 44 base repos. These are explicit
		// so the bootstrap remains deterministic while COPR packaging is built.
		"hyprland":                      "",
		"hyprpolkitagent":               "",
		"xdg-desktop-portal-hyprland":   "",
		"hypridle":                      "",
		"matugen":                       "",
		"vimix-cursors":                 "",
		"mpv-mpris":                     "",
		"spotify-launcher":              "",
		"spicetify-cli":                 "",
		"spicetify-marketplace":         "",
		"xpadneo-dkms":                  "",
		"game-devices-udev":             "",
		"broadcom-bt-firmware":          "",
		"blesh":                         "",
		"eza":                           "",
		"lazygit":                       "",
		"hyprpicker":                    "",
		"waifu2x-ncnn-vulkan":           "",
		"yazi":                          "",
		"songrec":                       "",
		"gpu-screen-recorder":           "",
		"hyprsunset":                    "",
		"noto-fonts":                    "",
		"noto-fonts-cjk":                "",
		"inter-font":                    "",
		"noto-fonts-emoji":              "",
		"ttf-jetbrains-mono-nerd":       "",
		"ttf-firacode-nerd":             "",
		"ttf-hack-nerd":                 "",
		"ttf-material-symbols-variable": "",
		"otf-space-grotesk":             "",
		"ttf-maple-mono-nf":             "",
	},
}

// activeDistro is set once by detectFacts; installed() reads it from the
// detection paths that have no engine to hand.
var activeDistro = archLinux

func detectDistro(id, like string) *distro {
	switch {
	case id == "arch" || strings.Contains(like, "arch"):
		return archLinux
	case id == "debian" || strings.Contains(like, "debian"):
		return debianLinux
	case id == "fedora" || strings.Contains(like, "fedora"):
		return fedoraLinux
	}
	return nil
}

// local returns the package's name on this distro, or "" when it does not exist.
func (d *distro) local(pkg string) string {
	if to, ok := d.rename[pkg]; ok {
		return to
	}
	if d.strictRename {
		return ""
	}
	return pkg
}

// localAll maps a base.packages list, dropping what this distro does not carry.
func (d *distro) localAll(pkgs []string) []string {
	out := make([]string, 0, len(pkgs))
	for _, p := range pkgs {
		if l := d.local(p); l != "" {
			out = append(out, l)
		}
	}
	return out
}

func (d *distro) installArgs(pkgs []string) []string {
	return append(append([]string{}, d.installCmd...), pkgs...)
}

func (d *distro) removeArgs(pkgs []string) []string {
	return append(append([]string{}, d.removeCmd...), pkgs...)
}

func (d *distro) installedPkg(pkg string) bool {
	args := append(append([]string{}, d.queryCmd[1:]...), pkg)
	out, err := exec.Command(d.queryCmd[0], args...).Output()
	if err != nil {
		return false
	}
	if d.id == "debian" {
		return strings.Contains(string(out), "install ok installed")
	}
	return true
}

// installed queries the detected distro. Replaces the old pacman-only helper.
func installed(pkg string) bool { return activeDistro.installedPkg(pkg) }

// d is the engine's detected distro; archLinux until detection says otherwise.
func (e *engine) d() *distro {
	if e.f != nil && e.f.distro != nil {
		return e.f.distro
	}
	return activeDistro
}

// ryokuBin finds the ryoku CLI: /usr/bin from a package, ~/.local/bin from a
// fromSource build. Empty when it is not installed yet.
func (e *engine) ryokuBin() string {
	cands := []string{"/usr/bin/ryoku"}
	if e.f != nil && e.f.homeDir != "" {
		cands = append(cands, filepath.Join(e.f.homeDir, ".local", "bin", "ryoku"))
	}
	for _, c := range cands {
		if fi, err := os.Stat(c); err == nil && !fi.IsDir() {
			return c
		}
	}
	return ""
}

// detectHostDistro resolves the distro from /etc/os-release and latches it, so
// the preflight gate and the later detection pass agree.
func detectHostDistro() *distro {
	b, err := os.ReadFile("/etc/os-release")
	if err != nil {
		return nil
	}
	id, like, _ := parseOSRelease(string(b))
	d := detectDistro(id, like)
	if d != nil {
		activeDistro = d
	}
	return d
}
