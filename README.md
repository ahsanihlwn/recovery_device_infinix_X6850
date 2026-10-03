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

Runtime validation on 2026-10-03: X6850 Android 16 boots normally with
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
