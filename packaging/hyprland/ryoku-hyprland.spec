# Ryoku-on-Fedora Hyprland package
#
# Derived in part from AshBuk/Hyprland-Fedora's MIT-licensed Fedora packaging:
# https://github.com/AshBuk/Hyprland-Fedora
# Copyright (c) 2025 Asher Buk
#
# Ryoku adaptation copyright (c) 2026 Ryoku-on-Fedora contributors
# SPDX-License-Identifier: MIT
#
# The packaged Hyprland project itself is BSD-3-Clause.

%global hyprland_version        0.56.2
%global hyprwayland_scanner_ver 0.4.6
%global hyprutils_ver           0.14.0
%global hyprlang_ver            0.6.8
%global hyprcursor_ver          0.1.13
%global hyprgraphics_ver        0.5.1
%global aquamarine_ver          0.14.0
%global hyprwire_ver            0.3.1
%global glaze_ver               7.2.0
%global lua_ver                 5.5.0
%global hypridle_version        0.1.8

Name:           ryoku-hyprland
Version:        %{hyprland_version}
Release:        0.1%{?dist}
Summary:        Ryoku-owned Hyprland compositor stack
License:        BSD-3-Clause
URL:            https://github.com/hyprwm/Hyprland

# Official Hyprland release archive. Unlike the GitHub-generated tag archive,
# this contains Hyprland's embedded hyprland-protocols and udis86 subprojects.
Source0:        https://github.com/hyprwm/Hyprland/releases/download/v%{hyprland_version}/source-v%{hyprland_version}.tar.gz

# Pinned Hyprland-specific libraries. They are built into a private prefix
# rather than replacing Fedora's system libhypr* packages.
Source20:       https://github.com/hyprwm/hyprwayland-scanner/archive/refs/tags/v%{hyprwayland_scanner_ver}.tar.gz#/hyprwayland-scanner-%{hyprwayland_scanner_ver}.tar.gz
Source21:       https://github.com/hyprwm/hyprutils/archive/refs/tags/v%{hyprutils_ver}.tar.gz#/hyprutils-%{hyprutils_ver}.tar.gz
Source22:       https://github.com/hyprwm/hyprlang/archive/refs/tags/v%{hyprlang_ver}.tar.gz#/hyprlang-%{hyprlang_ver}.tar.gz
Source23:       https://github.com/hyprwm/hyprcursor/archive/refs/tags/v%{hyprcursor_ver}.tar.gz#/hyprcursor-%{hyprcursor_ver}.tar.gz
Source24:       https://github.com/hyprwm/hyprgraphics/archive/refs/tags/v%{hyprgraphics_ver}.tar.gz#/hyprgraphics-%{hyprgraphics_ver}.tar.gz
Source25:       https://github.com/hyprwm/aquamarine/archive/refs/tags/v%{aquamarine_ver}.tar.gz#/aquamarine-%{aquamarine_ver}.tar.gz
Source26:       https://github.com/hyprwm/hyprwire/archive/refs/tags/v%{hyprwire_ver}.tar.gz#/hyprwire-%{hyprwire_ver}.tar.gz
Source27:       https://www.lua.org/ftp/lua-%{lua_ver}.tar.gz
Source30:       https://github.com/stephenberry/glaze/archive/refs/tags/v%{glaze_ver}.tar.gz#/glaze-%{glaze_ver}.tar.gz
Source40:       https://github.com/hyprwm/hypridle/archive/refs/tags/v%{hypridle_version}.tar.gz#/hypridle-%{hypridle_version}.tar.gz

BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  pkgconf-pkg-config
BuildRequires:  python3
BuildRequires:  cairo-devel
BuildRequires:  glm-devel
BuildRequires:  glslang-devel
BuildRequires:  hwdata
BuildRequires:  libdisplay-info-devel
BuildRequires:  libdrm-devel
BuildRequires:  libepoxy-devel
BuildRequires:  mesa-libgbm-devel
BuildRequires:  mesa-libEGL-devel
BuildRequires:  libglvnd-devel
BuildRequires:  libglvnd-gles
BuildRequires:  libinput-devel >= 1.29
BuildRequires:  libeis-devel
BuildRequires:  readline-devel
BuildRequires:  libjxl-devel
BuildRequires:  libliftoff-devel
BuildRequires:  libspng-devel
BuildRequires:  libwebp-devel
BuildRequires:  libxcb-devel
BuildRequires:  libXcursor-devel
BuildRequires:  libxcvt-devel
BuildRequires:  libxkbcommon-devel
BuildRequires:  pango-devel
BuildRequires:  pixman-devel
BuildRequires:  pugixml-devel
BuildRequires:  re2-devel
BuildRequires:  scdoc
BuildRequires:  libseat-devel
BuildRequires:  systemd-devel
BuildRequires:  tomlplusplus-devel
BuildRequires:  wayland-devel
BuildRequires:  wayland-protocols-devel >= 1.35
BuildRequires:  libzip-devel
BuildRequires:  librsvg2-devel
BuildRequires:  libjpeg-turbo-devel
BuildRequires:  libpng-devel
BuildRequires:  file-devel
BuildRequires:  xcb-util-devel
BuildRequires:  xcb-util-errors-devel
BuildRequires:  xcb-util-image-devel
BuildRequires:  xcb-util-renderutil-devel
BuildRequires:  xcb-util-wm-devel
BuildRequires:  xorg-x11-server-Xwayland
BuildRequires:  libXfont2-devel
BuildRequires:  xkeyboard-config
BuildRequires:  glib2-devel
BuildRequires:  libuuid-devel
BuildRequires:  libffi-devel
BuildRequires:  muParser-devel
BuildRequires:  sdbus-cpp-devel >= 2.0.0

Requires:       cairo
Requires:       hwdata
Requires:       libdisplay-info
Requires:       libdrm
Requires:       libepoxy
Requires:       mesa-libgbm
Requires:       libinput >= 1.29
Requires:       libeis
Requires:       readline
Requires:       libjxl
Requires:       libliftoff
Requires:       libspng
Requires:       libwebp
Requires:       libxcb
Requires:       libXcursor
Requires:       libxcvt
Requires:       libxkbcommon
Requires:       pango
Requires:       pixman
Requires:       pugixml
Requires:       re2
Requires:       libseat
Requires:       libwayland-client
Requires:       libwayland-server
Requires:       libzip
Requires:       librsvg2
Requires:       xcb-util
Requires:       xcb-util-errors
Requires:       xcb-util-image
Requires:       xcb-util-renderutil
Requires:       xcb-util-wm
Requires:       xorg-x11-server-Xwayland
Requires:       libffi
Requires:       muParser
Recommends:     ryoku-hypridle = %{version}-%{release}

%description
Hyprland packaged as the compositor ABI owned by Ryoku-on-Fedora.

Hyprland-specific libraries are built from fixed upstream versions and placed
under %{_libexecdir}/ryoku-hyprland/vendor so they do not replace Fedora's
system libraries. Fedora continues to own the kernel, graphics drivers, Mesa,
SELinux and the rest of the host operating system.

%package devel
Summary:        Development files for the Ryoku Hyprland ABI
Requires:       %{name}%{?_isa} = %{version}-%{release}
Requires:       pkgconf-pkg-config

%description devel
Hyprland headers plus the private, version-matched dependency headers and
pkg-config metadata used to build Ryoku's compositor plugins against exactly
the ABI shipped by ryoku-hyprland.

%package -n ryoku-hypridle
Summary:        Hyprland idle daemon built against Ryoku's compositor ABI
License:        BSD-3-Clause
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description -n ryoku-hypridle
Pinned hypridle build for the Ryoku-on-Fedora Hyprland stack.

%prep
%setup -q -n hyprland-source

tar -xzf %{SOURCE20}
tar -xzf %{SOURCE21}
tar -xzf %{SOURCE22}
tar -xzf %{SOURCE23}
tar -xzf %{SOURCE24}
tar -xzf %{SOURCE25}
tar -xzf %{SOURCE26}
tar -xzf %{SOURCE27}
tar -xzf %{SOURCE30}
tar -xzf %{SOURCE40}

%build
# Some Fedora hwdata builds do not expose hwdata.pc even though Hyprland checks
# it through pkg-config.
mkdir -p pkgconfig
cat > pkgconfig/hwdata.pc <<'EOF'
prefix=/usr
datarootdir=${prefix}/share
pkgdatadir=${datarootdir}/hwdata

Name: hwdata
Description: Hardware identification databases
Version: 0.385
EOF

VENDOR_PREFIX="$(pwd)/vendor"
export PATH="$VENDOR_PREFIX/bin:$PATH"
export PKG_CONFIG_PATH="$VENDOR_PREFIX/lib64/pkgconfig:$VENDOR_PREFIX/lib/pkgconfig:$(pwd)/pkgconfig:%{_libdir}/pkgconfig:%{_datadir}/pkgconfig"
export CMAKE_PREFIX_PATH="$VENDOR_PREFIX"
export OPENGL_opengl_LIBRARY=%{_libdir}/libOpenGL.so
export OPENGL_gles3_LIBRARY=%{_libdir}/libGLESv2.so
export OPENGL_GLES3_INCLUDE_DIR=/usr/include
export OPENGL_egl_LIBRARY=%{_libdir}/libEGL.so
export OPENGL_EGL_INCLUDE_DIR=/usr/include
export OPENGL_INCLUDE_DIR=/usr/include

# Keep sibling private libraries discoverable when they are later copied under
# /usr/libexec/ryoku-hyprland/vendor.
VENDOR_RPATH='\$ORIGIN'

pushd hyprwayland-scanner-%{hyprwayland_scanner_ver}
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$VENDOR_PREFIX" \
  -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_RPATH="$VENDOR_RPATH"
cmake --build build --parallel %{_smp_build_ncpus}
cmake --install build
popd

for component in \
  hyprutils-%{hyprutils_ver} \
  hyprlang-%{hyprlang_ver} \
  hyprcursor-%{hyprcursor_ver} \
  hyprgraphics-%{hyprgraphics_ver} \
  hyprwire-%{hyprwire_ver}
do
  pushd "$component"
  cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$VENDOR_PREFIX" \
    -DCMAKE_PREFIX_PATH="$VENDOR_PREFIX" -DCMAKE_INSTALL_LIBDIR=lib64 \
    -DCMAKE_INSTALL_RPATH="$VENDOR_RPATH"
  cmake --build build --parallel %{_smp_build_ncpus}
  cmake --install build
  popd
done

pushd aquamarine-%{aquamarine_ver}
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$VENDOR_PREFIX" \
  -DCMAKE_PREFIX_PATH="$VENDOR_PREFIX" -DCMAKE_INSTALL_LIBDIR=lib64 \
  -Dhyprwayland-scanner_DIR="$VENDOR_PREFIX/lib64/cmake/hyprwayland-scanner" \
  -DCMAKE_INSTALL_RPATH="$VENDOR_RPATH" \
  -DOpenGL_GL_PREFERENCE=GLVND \
  -DOPENGL_opengl_LIBRARY=%{_libdir}/libOpenGL.so \
  -DOPENGL_gles3_LIBRARY=%{_libdir}/libGLESv2.so \
  -DOPENGL_GLES3_INCLUDE_DIR=/usr/include \
  -DOPENGL_egl_LIBRARY=%{_libdir}/libEGL.so \
  -DOPENGL_EGL_INCLUDE_DIR=/usr/include \
  -DOPENGL_INCLUDE_DIR=/usr/include
cmake --build build --parallel %{_smp_build_ncpus}
cmake --install build
popd

# hyprland-protocols and udis86 are already included by the official source
# archive. Install the protocols into the private dependency prefix.
pushd subprojects/hyprland-protocols
meson setup build --prefix="$VENDOR_PREFIX" --libdir=lib64
ninja -C build
ninja -C build install
popd

pushd glaze-%{glaze_ver}
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$VENDOR_PREFIX" \
  -Dglaze_DEVELOPER_MODE=OFF -DBUILD_TESTING=OFF
cmake --install build
popd

pushd lua-%{lua_ver}
make MYCFLAGS="-fPIC -fvisibility=hidden" linux %{?_smp_mflags}
make install INSTALL_TOP="$VENDOR_PREFIX" INSTALL_LIB="$VENDOR_PREFIX/lib64"
mkdir -p "$VENDOR_PREFIX/lib64/pkgconfig"
cat > "$VENDOR_PREFIX/lib64/pkgconfig/lua5.5.pc" <<EOF
Name: Lua
Description: An Extensible Extension Language
Version: %{lua_ver}
Libs: -L$VENDOR_PREFIX/lib64 -llua -lm -ldl
Cflags: -I$VENDOR_PREFIX/include
EOF
popd

export GIT_TAG="v%{hyprland_version}"
export GIT_BRANCH="v%{hyprland_version}"
export GIT_COMMIT_HASH="release-v%{hyprland_version}"
export GIT_COMMIT_MESSAGE="Release v%{hyprland_version}"
export GIT_COMMIT_DATE="$(date -u -d "@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y-%m-%d)"
export GIT_DIRTY=""
export GIT_COMMITS="0"

HYPR_RPATH='\$ORIGIN/../libexec/ryoku-hyprland/vendor/lib64:\$ORIGIN/../libexec/ryoku-hyprland/vendor/lib'
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=%{_prefix} \
  -DCMAKE_PREFIX_PATH="$VENDOR_PREFIX" \
  -Dhyprwayland-scanner_DIR="$VENDOR_PREFIX/lib64/cmake/hyprwayland-scanner" \
  -DCMAKE_CXX_FLAGS="%{optflags} -I$VENDOR_PREFIX/include" \
  -DBUILD_TESTING=OFF \
  -DCMAKE_INSTALL_RPATH="$HYPR_RPATH" \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  -DOPENGL_opengl_LIBRARY=%{_libdir}/libOpenGL.so \
  -DOPENGL_gles3_LIBRARY=%{_libdir}/libGLESv2.so \
  -DOPENGL_GLES3_INCLUDE_DIR=/usr/include \
  -DOPENGL_egl_LIBRARY=%{_libdir}/libEGL.so \
  -DOPENGL_EGL_INCLUDE_DIR=/usr/include \
  -DOPENGL_INCLUDE_DIR=/usr/include
cmake --build build --parallel %{_smp_build_ncpus}

pushd hypridle-%{hypridle_version}
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=%{_prefix} \
  -DCMAKE_PREFIX_PATH="$VENDOR_PREFIX" \
  -Dhyprwayland-scanner_DIR="$VENDOR_PREFIX/lib64/cmake/hyprwayland-scanner" \
  -DCMAKE_CXX_FLAGS="%{optflags} -I$VENDOR_PREFIX/include" \
  -DCMAKE_INSTALL_RPATH="$HYPR_RPATH" \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
cmake --build build --parallel %{_smp_build_ncpus}
popd

%install
VENDOR_PREFIX="$(pwd)/vendor"
VENDOR_DST="%{buildroot}%{_libexecdir}/ryoku-hyprland/vendor"

DESTDIR=%{buildroot} cmake --install build
ln -sf Hyprland %{buildroot}%{_bindir}/hyprland

# Runtime part of the private dependency closure.
install -d "$VENDOR_DST/lib64"
cp -a "$VENDOR_PREFIX"/lib64/lib*.so* "$VENDOR_DST/lib64/" 2>/dev/null || true

# Development part of the same closure. These files live in a private prefix;
# plugin specs opt into them via PKG_CONFIG_PATH/CMAKE_PREFIX_PATH.
cp -a "$VENDOR_PREFIX"/include "$VENDOR_DST/" 2>/dev/null || true
cp -a "$VENDOR_PREFIX"/lib64/pkgconfig "$VENDOR_DST/lib64/" 2>/dev/null || true
cp -a "$VENDOR_PREFIX"/lib64/cmake "$VENDOR_DST/lib64/" 2>/dev/null || true
cp -a "$VENDOR_PREFIX"/share "$VENDOR_DST/" 2>/dev/null || true

# Hyprland's generated pc file names the vendored hypr* modules in Requires.
# Keep that original metadata in the private prefix and install a public pc file
# whose Cflags explicitly include the private headers. Ryoku plugin RPMs set
# PKG_CONFIG_PATH to the private directory when they need dependency metadata.
if [ -f %{buildroot}%{_datadir}/pkgconfig/hyprland.pc ]; then
  install -Dm644 %{buildroot}%{_datadir}/pkgconfig/hyprland.pc \
    "$VENDOR_DST/share/pkgconfig/hyprland.pc"
fi
cat > %{buildroot}%{_datadir}/pkgconfig/hyprland.pc <<EOF
prefix=/usr
includedir=/usr/include
vendor=%{_libexecdir}/ryoku-hyprland/vendor

Name: Hyprland
URL: https://github.com/hyprwm/Hyprland
Description: Ryoku-pinned Hyprland header files
Version: %{hyprland_version}
Requires: libdrm, egl, cairo, xkbcommon, libinput, wayland-server
Cflags: -I\${includedir} -I\${includedir}/hyprland/protocols -I\${includedir}/hyprland -I\${includedir}/hyprland/src -I\${vendor}/include
EOF

DESTDIR=%{buildroot} cmake --install hypridle-%{hypridle_version}/build

%check
test -x build/Hyprland || test -x build/src/Hyprland
test -f build/hyprland.pc

%files
%license LICENSE
%doc README.md
%{_bindir}/Hyprland
%{_bindir}/hyprland
%{_bindir}/hyprctl
%{_bindir}/hyprpm
%{_bindir}/start-hyprland
%dir %{_libexecdir}/ryoku-hyprland
%dir %{_libexecdir}/ryoku-hyprland/vendor
%{_libexecdir}/ryoku-hyprland/vendor/lib64/*.so*
%{_datadir}/wayland-sessions/hyprland.desktop
%{_datadir}/wayland-sessions/hyprland-uwsm.desktop
%{_datadir}/hypr/
%exclude %{_datadir}/hypr/hypridle.conf
%{_datadir}/xdg-desktop-portal/hyprland-portals.conf
%{_mandir}/man1/Hyprland.1*
%{_mandir}/man1/hyprctl.1*
%{_datadir}/bash-completion/completions/hyprctl
%{_datadir}/bash-completion/completions/hyprpm
%{_datadir}/fish/vendor_completions.d/hyprctl.fish
%{_datadir}/fish/vendor_completions.d/hyprpm.fish
%{_datadir}/zsh/site-functions/_hyprctl
%{_datadir}/zsh/site-functions/_hyprpm

%files devel
%{_includedir}/hyprland/
%{_datadir}/pkgconfig/hyprland.pc
%{_libexecdir}/ryoku-hyprland/vendor/include/
%{_libexecdir}/ryoku-hyprland/vendor/lib64/pkgconfig/
%{_libexecdir}/ryoku-hyprland/vendor/lib64/cmake/
%{_libexecdir}/ryoku-hyprland/vendor/share/

%files -n ryoku-hypridle
%license hypridle-%{hypridle_version}/LICENSE
%{_bindir}/hypridle
%{_userunitdir}/hypridle.service
%{_datadir}/hypr/hypridle.conf

%changelog
* Wed Sep 02 2026 Ryoku-on-Fedora contributors - 0.56.2-0.1
- Initial Ryoku-owned Fedora compositor ABI package
- Use Hyprland's official release archive with embedded subprojects
- Keep Hyprland-specific libraries under a private Ryoku prefix
