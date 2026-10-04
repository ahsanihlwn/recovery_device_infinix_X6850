# OrangeFox 14.1 — Infinix Note 40 (X6853)

Unofficial device tree for Android 16. Branch: `fox_14.1_X6853`.

## Target

| Item | Value |
| --- | --- |
| Device | `X6853` |
| Platform | MT6789 / arm64 |
| Firmware | Android 16 / SDK 36 |
| ODM build | `301450022` |
| Vendor security patch | `2026-08-01` |
| Kernel module ABI | `6.12.38-android16-5-gcc51d883045d-4k` |
| PLATFORM modules | 237 modules + 5 stock metadata files |

## Build

Use an OrangeFox 14.1 checkout with this branch at `device/infinix/X6853`.
Keep one device-family tree in the build source scan.

```bash
source build/envsetup.sh
source device/infinix/X6853/vendorsetup.sh
lunch twrp_X6853-ap2a-eng
mka adbd vendorbootimage
```

## Output

```text
out/target/product/X6853/vendor_boot.img
out/target/product/X6853/OrangeFox-*.zip
```

`OUT_DIR` overrides the output prefix. The build produces native PLATFORM and
RECOVERY ramdisks; no stock reference image or post-build repacking is required.

## Contributors

- [ahsanihlwn](https://github.com/ahsanihlwn)
- [ardiandideyashidiq](https://github.com/ardiandideyashidiq)
- [Andrikurn](https://github.com/Andrikurn)
