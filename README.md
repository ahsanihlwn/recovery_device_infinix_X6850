# OrangeFox 14.1 — Infinix Note 40S (X6850B)

Unofficial device tree for Android 16. Branch: `fox_14.1_X6850B`.

## Target

| Item | Value |
| --- | --- |
| Device | `X6850B` |
| Platform | MT6789 / arm64 |
| Firmware | Android 16 / SDK 36 |
| ODM build | `301450017` |
| Vendor security patch | `2026-08-01` |
| Kernel module ABI | `6.12.38-android16-5-gcc51d883045d-4k` |
| PLATFORM modules | 233 modules + 5 stock metadata files |

## Build

Use an OrangeFox 14.1 checkout with this branch at `device/infinix/X6850B`.
Keep one device-family tree in the build source scan.

```bash
source build/envsetup.sh
source device/infinix/X6850B/vendorsetup.sh
lunch twrp_X6850B-ap2a-eng
mka adbd vendorbootimage
```

## Output

```text
out/target/product/X6850B/vendor_boot.img
out/target/product/X6850B/OrangeFox-*.zip
```

`OUT_DIR` overrides the output prefix. The build produces native PLATFORM and
RECOVERY ramdisks; no stock reference image or post-build repacking is required.

## Contributors

- [ahsanihlwn](https://github.com/ahsanihlwn)
- [ardiandideyashidiq](https://github.com/ardiandideyashidiq)
- [Andrikurn](https://github.com/Andrikurn)
