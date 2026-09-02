# Prepare the Fedora 44 Ryoku validation VM from CachyOS

This document prepares the disposable VM used by `docs/PHASE1_VM_VALIDATION.md`.

Do **not** install the Fedora port on the CachyOS host itself.

## 1. Install the KVM/libvirt tooling on CachyOS

```fish
sudo pacman -S --needed qemu-full virt-manager swtpm
```

Enable libvirt's QEMU connection:

```fish
sudo systemctl enable --now libvirtd.socket
```

For VM/domain autostart support it is also safe to enable the service:

```fish
sudo systemctl enable --now libvirtd.service
```

Add your user to the libvirt group:

```fish
sudo usermod -aG libvirt $USER
```

Then **log out of Ryoku and log back in** so the new group membership applies.

Confirm:

```fish
groups
systemctl status libvirtd.socket --no-pager
virsh -c qemu:///system list --all
```

If `libvirt` appears in `groups` and `virsh` returns a VM list without an authorization error, the host is ready.

## 2. Download Fedora Workstation 44

Use the official Fedora Workstation 44 **x86_64 Live ISO**.

Fedora currently publishes the Fedora 44 Workstation image with SHA-256:

```text
1620295f6a00c27c3208f0c00b8ece4eab1ec69b9002152d97488bf26a426ddf
```

After the ISO downloads, verify it. If it is in `~/Downloads`:

```fish
cd ~/Downloads
sha256sum Fedora-Workstation-Live-44-*.x86_64.iso
```

The printed hash must match the value above.

## 3. Create the VM in Virtual Machine Manager

Launch:

```fish
virt-manager
```

Create a new VM with **Local install media (ISO image)** and select the Fedora 44 Workstation ISO.

Recommended test-machine configuration:

- OS: Fedora 44
- Firmware: UEFI / OVMF
- CPUs: 8 vCPUs
- RAM: 12 GiB minimum; 16 GiB is comfortable
- Disk: 80 GiB qcow2
- Network: libvirt default NAT
- Video/display: the normal virt-manager SPICE/Virtio defaults are fine
- Secure Boot: not required for this Phase 1 test

Do not configure GPU passthrough. The purpose of this VM is session/integration validation, not graphics benchmarking.

## 4. Install Fedora normally

Boot the ISO and install **Fedora Workstation 44** normally.

Important:

- keep the default Fedora partitioning/boot path
- keep SELinux enabled
- keep GNOME and GDM
- do not install SDDM
- do not install a third-party Hyprland COPR
- do not disable Secure Boot/SELinux inside Fedora merely to make Ryoku work

After installation, reboot into Fedora and complete the first-login setup.

## 5. Update the clean Fedora VM once

Inside the Fedora VM:

```bash
sudo dnf upgrade --refresh
```

Reboot if Fedora installs a newer kernel:

```bash
sudo reboot
```

After reboot, confirm:

```bash
cat /etc/fedora-release
getenforce
systemctl is-enabled gdm.service
systemctl is-enabled NetworkManager.service
```

Expected:

- Fedora release is 44
- SELinux is `Enforcing`
- GDM is enabled
- NetworkManager is enabled

## 6. Take the clean snapshot

Shut the VM down completely.

In virt-manager:

1. Open the Fedora VM.
2. Open the VM details/snapshot interface.
3. Create a snapshot named:

```text
fedora44-clean-before-ryoku
```

This snapshot is mandatory. If Ryoku damages the VM state, revert to this snapshot instead of attempting to repair the test baseline.

## 7. Clone the Ryoku-on-Fedora test branch inside the VM

Boot Fedora again and install Git:

```bash
sudo dnf install -y git
```

Then:

```bash
git clone -b phase1-safe-session https://github.com/ashmitvoid/Ryoku-on-Fedora.git
cd Ryoku-on-Fedora
```

Do **not** run the Ryoku installer yet.

## Stop point

At this stage your VM should be:

- Fedora 44 Workstation
- SELinux Enforcing
- still using GDM
- still booting the stock Fedora kernel
- connected to the Internet
- snapshotted as `fedora44-clean-before-ryoku`
- checked out to `Ryoku-on-Fedora/phase1-safe-session`

Wait for the `fedora44-rpm-build` CI gate to pass before moving to `docs/PHASE1_VM_VALIDATION.md`.

The next user action after that gate is to download the `ryoku-hyprland-fedora44-rpms` GitHub Actions artifact into this VM and run the repository's guarded compositor installer.
