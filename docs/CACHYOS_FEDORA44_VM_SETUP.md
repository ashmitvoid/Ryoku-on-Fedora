# Prepare the Fedora 44 validation VM with Ryoport

Ryoku already ships **Ryoport**, its QEMU/KVM machine hub. Use it for the Fedora 44 Phase 1 validation VM instead of installing a second VM frontend such as virt-manager.

Ryoport is backed by Quickemu/Quickget and QEMU/KVM. It supports local ISO imports, per-machine CPU/RAM/display configuration, normal snapshots, and a reserved **Seal** that can be restored after a destructive test.

Do **not** install Ryoku-on-Fedora on the CachyOS/Ryoku host itself.

## 1. Open Ryoport

Use the Ryoku keybind:

```text
Super + Shift + V
```

or launch it from the app launcher as **Ryoport**.

Open:

```text
Machines
```

If Ryoport shows an **ENGINE OFFLINE** banner, use its **INSTALL ENGINE** action. Ryoport can manage/import machine definitions without Quickemu, but launching them requires the Quickemu/QEMU engine.

If Ryoport says **Virtualization is off**, enable SVM/AMD-V in firmware before continuing.

## 2. Download Fedora Workstation 44

Download the official Fedora Workstation 44 x86_64 Live ISO.

Verify the ISO with Fedora's published checksum before using it.

Keep the ISO on the host, for example under:

```text
~/Downloads/
```

## 3. Create the Fedora VM through the ISO channel

In Ryoport:

```text
Machines
  → NEW
  → ISO
```

Use:

```text
Name:       fedora44-ryoku-test
ISO file:   <Fedora Workstation 44 x86_64 Live ISO>
Guest type: LINUX
```

Press **CREATE**.

Ryoport's ISO importer lets Quickemu choose the initial Linux defaults. After the machine appears in **LIBRARY**, select it and tune the machine to approximately:

```text
CPU:      8 vCPUs
RAM:      16 GiB
Disk:     80 GiB or larger
Display:  WINDOW or SPICE
UEFI:     enabled
TPM:      not required
```

No GPU passthrough is required. This VM validates the Ryoku session/integration path, not graphics performance.

If SPICE is unavailable on the host, use **WINDOW** mode. Ryoport's plain window mode is sufficient for this test.

## 4. First launch and Fedora installation

Launch the VM **normally**.

Do **not** enable Ryoport's **DISPOSABLE** switch during installation. A disposable launch uses Quickemu `--status-quo`, so disk writes disappear at power-off.

Install Fedora Workstation 44 normally.

Keep:

- Fedora's normal partitioning and boot path
- GNOME
- GDM
- SELinux
- NetworkManager
- Fedora's stock kernel

Do not:

- install SDDM
- install a third-party Hyprland COPR
- disable SELinux
- replace Fedora's bootloader
- add GPU passthrough

After Fedora installation finishes, power the VM off and launch it normally again so it boots from the installed virtual disk.

## 5. Update the clean Fedora guest once

Inside Fedora:

```bash
sudo dnf upgrade --refresh
```

Reboot when appropriate:

```bash
sudo reboot
```

Then confirm:

```bash
cat /etc/fedora-release
getenforce
systemctl is-enabled gdm.service
systemctl is-enabled NetworkManager.service
```

Expected state:

- Fedora release 44
- SELinux `Enforcing`
- GDM enabled
- NetworkManager enabled

## 6. Clone the Fedora port but do not install it

Inside the Fedora guest:

```bash
sudo dnf install -y git
git clone -b phase1-safe-session https://github.com/ashmitvoid/Ryoku-on-Fedora.git
cd Ryoku-on-Fedora
git branch --show-current
```

The branch must be:

```text
phase1-safe-session
```

Do not run the Ryoku installer yet.

## 7. Power off and Seal the clean Fedora state

Shut Fedora down completely.

Back in Ryoport, select `fedora44-ryoku-test` and use **SEAL**.

The Seal is Ryoport's reserved golden-state qcow2 snapshot. This is the equivalent of the mandatory clean pre-Ryoku VM snapshot for Phase 1.

The machine must be powered off before treating this Seal as the clean validation baseline.

## 8. Important: normal vs disposable launches

For the actual Ryoku installation/test:

- launch **normally**
- leave **DISPOSABLE OFF**

We need the Ryoku installation to survive reboot/logout so we can test GDM → Ryoku → GNOME fallback → uninstall.

Use **DISPOSABLE** only for optional exploratory tests where you explicitly want every write discarded at shutdown.

If a destructive Phase 1 test leaves the guest unusable:

1. power it off
2. select the machine in Ryoport
3. use **RESTORE SEAL**
4. launch normally again

The VM should return to the exact clean Fedora state recorded by the Seal.

## Stop point

The user-side preparation is complete when:

- Fedora 44 Workstation is installed in Ryoport
- SELinux is Enforcing
- GDM and NetworkManager are enabled
- `Ryoku-on-Fedora/phase1-safe-session` is cloned inside the guest
- the VM is powered off
- the clean guest has been **SEALED**
- no Ryoku-on-Fedora installer has been run

Only after the Fedora compositor RPM CI gate is green should the destructive Phase 1 sequence in `docs/PHASE1_VM_VALIDATION.md` begin.
