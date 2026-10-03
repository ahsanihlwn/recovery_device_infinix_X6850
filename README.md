# OrangeFox 14.1 for Infinix Note 40S (X6850B)

Branch: `fox_14.1_X6850B`. Derived from the native X6850 tree at `ec1f19b`.

## Build

```bash
git clone https://github.com/ahsanihlwn/recovery_device_infinix_X6850.git \
  -b fox_14.1_X6850B device/infinix/X6850B
source build/envsetup.sh
source device/infinix/X6850B/vendorsetup.sh
lunch twrp_X6850B-ap2a-eng
mka adbd vendorbootimage
```

Use an OrangeFox 14.1 source checkout. Keep only the selected device tree in its
build source scan: sibling clones provide duplicate MTK boot-control modules.
The output is `out/target/product/X6850B/vendor_boot.img` and an OrangeFox ZIP.
An `OUT_DIR` override changes the output prefix.

## Native Android 16 bootstrap

The source pipeline builds a static first-stage init and creates separate ZSTD
PLATFORM and RECOVERY fragments. The device's 233 stock modules and five
metadata files are installed into PLATFORM. `common/mt6789-vendor16` and patch 04
provide the native build rules. No stock image or post-build PLATFORM replacement
is used. Legacy repack tools remain available for manual analysis and are not
enabled by `vendorsetup.sh`.

Target firmware: Android 16, SDK 36, incremental `301450017`, security patch
`2026-08-01`, kernel module ABI
`6.12.38-android16-5-gcc51d883045d-4k`.

Replaces tc_hl7139a.ko with tc_sc8548_charger.ko. All module dependency, alias and recovery load metadata comes from
this device's original PLATFORM fragment. DTB, first-stage fstab, offsets and
bootconfig match the X6850 baseline byte for byte. Stock ODM density: 440 (recorded in BoardConfig).
The touch modules and firmware were checked against this device's ODM inputs.
The inherited adaptive-ts recovery bootmode patch is still required.

## Validation status

Source build and image/ZIP checks passed on 2026-10-04. The checks verify static
init, target module/firmware bytes, product identity, ZSTD fragments, DTB/fstab,
AVB hash and matching installer contents.

The native bootstrap has passed Android normal boot through `system_server` and
recovery/decryption checks on **X6850**. X6850B has not been tested on physical
hardware. Display, touch, decryption, USB and normal Android boot remain pending
on X6850B; shared inputs alone do not prove those runtime results.

See [device adaptation notes](docs/native-vendor16.md) for the source changes,
dump evidence and build checks.
