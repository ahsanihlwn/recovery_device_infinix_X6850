## OrangeFox device tree for Infinix Note 40 Pro 4G (_X6850_)

## Device picture

<p align="left" width="100%">
<img width="33%" src="https://fdn2.gsmarena.com/vv/pics/infinix/infinix-note-40-pro-4g-2.jpg"> 
</p>

## Device specifications

Device                  | Infinix Note 40 Pro 4G
-----------------------:|:-----------------------------------------
Model                   | X6850
Released                | 2024, March 19
SoC                     | MediaTek Helio G99 Ultimate
CPU                     | Octa-core (2x2.2 GHz Cortex-A76 & 6x2.0 GHz Cortex-A55)
GPU                     | Mali-G57 MC2
Memory                  | 8/12 GB RAM
Storage                 | 256 GB (UFS 2.2)
MicroSD                 | Unspecified
Shipped Android Version | 14 (XOS 14)
Battery                 | Non-removable 5000 mAh
Charging                | 70W wired (50% in 20 min), 20W wireless MagCharge
Display                 | 1080 x 2436 pixels (~393 ppi density), 6.78 inches, AMOLED 120Hz
Camera                  | 108 MP (wide) + 2 MP + 2 MP; 32 MP (front)
Body                    | 164.4 x 74.6 x 7.8 mm, 190 g
Protection              | IP54
Colors                  | Vintage Green, Titan Gold, Racing Edition

## Features

- [X] ADB
- [X] Decryption
- [X] Display
- [X] Fasbootd
- [X] Flashing
- [X] MTP
- [X] Sideload
- [X] USB OTG
- [X] Vibrator

## Building

Sync OrangeFox 14.1 Manifest:

```
git clone https://gitlab.com/OrangeFox/sync.git
cd sync
./orangefox_sync.sh --branch 14.1 --path ~/fox_14.1
```

Clone the device tree:

```
cd ~/fox_14.1
git clone https://github.com/ahsanihlwn/recovery_device_infinix_X6850.git -b fox_14.1_X6850 ./device/infinix/X6850
```

The build produces PLATFORM and RECOVERY ramdisks natively. PLATFORM contains a source-built first-stage init, the device fstab, and kernel modules matching the Android 16 firmware. No stock vendor_boot image is needed during the build.

### Native vendor bootstrap

The shared build configuration is in `common/mt6789-vendor16`. The device supplies
`MTK_VENDOR16_RAMDISK_MODULES_DIR` and `MTK_VENDOR16_RAMDISK_FSTABS` before inheriting
`vendor_ramdisk.mk`, and includes the common `BoardConfig.mk`.

`prebuilt/modules` holds the original kernel modules and their load/dependency
metadata. They are installed only into PLATFORM and are available in both boot
modes. Recovery-specific touch modules remain under `recovery/root/lib/modules/touch`.
The build creates the root directories needed by first-stage init before packing
PLATFORM. Android normal boot then continues with the init on the system partition.

Runtime validation of the 2026-10-03 baseline: X6850 Android 16 boots normally with
`sys.boot_completed=1` and a running `system_server`; OrangeFox boots, decrypts
user 0, and registers the `mtk-tpd` touch input. The flashed partition was read
back and matched the native build. Other devices have not been runtime tested.

Use each device's matching module set, recovery load order, fstab, DTB and boot
properties. The configuration was derived from Android 16 dumps for X6850, X6850B
and X6853; other firmware families need their own compatibility checks.

Build:

```
source build/envsetup.sh
lunch twrp_X6850-ap2a-eng && mka adbd vendorbootimage
```


### Device utility

`tools/patch_adaptive_ts.py` is a manual generator for the audited recovery touch
module; see [its usage notes](tools/README.md). The native build consumes the
prepared module and does not invoke this utility. Obsolete vendor_boot repacking
scripts and the unused X6850 stock reference image have been removed.

Patch 03 is retained only so `vendorsetup.sh` can reverse its old installer hook
in a previously patched checkout. Native setup applies patches 04/05/06.

### Recovery SELinux

The recovery policy is built with no permissive domains. Patch 05 supplies the
enforcing init/service setup and the native file-contexts build dependency fix.
Patch 06 checks the native Gatekeeper-to-keystore auth-token handoff. Metadata,
DE and credential-protected CE decryption must be validated separately.
See [the shared policy notes](common/mt6789-vendor16/sepolicy/README.md) for the
userdata/FBE rules, build checks and physical-device validation requirements.
Feature support must be verified again on the enforcing build for each model.


### Enforcing validation on 2026-10-04

The common native init, enforcing policy and credential-token fixes are identical
across X6850, X6853 and X6850B. All three target images were rebuilt and validated
with zero permissive domains and compiler neverallow checks enabled. Target
modules, firmware, product identity and density remain model specific.

X6850 was physically tested with the updated build: recovery/ADB works,
credential-protected user-0 CE decryption succeeds, and normal Android reaches
`sys.boot_completed=1` with a stable `system_server`. Fastbootd mode entry works;
full partition-operation support has not been certified. X6853 and X6850B still
require physical testing on their corresponding models.
