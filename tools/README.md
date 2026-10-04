# Recovery touch utility

`patch_adaptive_ts.py` regenerates the recovery-only adaptive-ts module from the
audited stock AArch64 module. It changes the recovery boot-mode mask at offset
0x5e80, checks the input SHA256 and changes exactly one byte. The source file
is preserved; use a separate output path.

```bash
python3 tools/patch_adaptive_ts.py /path/to/stock/adaptive-ts.ko \
  recovery/root/lib/modules/touch/adaptive-ts.ko
```

This is a manual utility for refreshing the touch prebuilt. Normal builds consume
the module already stored under recovery/root/lib/modules/touch. PLATFORM modules
come from the selected device's prebuilt/modules directory.

The obsolete vendor_boot repacker and postprocessor have been removed. The native
build packages PLATFORM and RECOVERY directly through patch 04 and the common
MT6789 vendor16 build configuration.
