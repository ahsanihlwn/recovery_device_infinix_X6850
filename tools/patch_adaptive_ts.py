#!/usr/bin/env python3
import argparse
import hashlib
import struct
from pathlib import Path

SOURCE_SHA256 = "8f49890f5036e9f0bdec49131ae600cbb85e14ddf84e848bd5db24fc87292052"
SOURCE_SIZE = 300792
PATCH_OFFSET = 0x5E80
ORIGINAL = bytes.fromhex("89608052")
REPLACEMENT = bytes.fromhex("09608052")


def boot_mode_result(mode, denied_modes):
    if mode > 9:
        return 0
    if (1 << mode) & 0x52:
        return 2
    return int(bool((1 << mode) & denied_modes))


def patch_module(source, destination):
    data = source.read_bytes()
    if len(data) != SOURCE_SIZE or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Input is not the audited stock adaptive-ts.ko; refusing to patch")
    if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<HH", data, 16) != (1, 183):
        raise ValueError("Expected an AArch64 ELF64 little-endian relocatable module")
    if data[PATCH_OFFSET:PATCH_OFFSET + 4] != ORIGINAL:
        raise ValueError("Recovery boot-mode mask instruction does not match")
    original_mapping = [boot_mode_result(mode, 0x304) for mode in range(16)]
    patched_mapping = [boot_mode_result(mode, 0x300) for mode in range(16)]
    if [mode for mode in range(16) if original_mapping[mode] != patched_mapping[mode]] != [2]:
        raise ValueError("Patch must change recovery mode 2 only")
    patched = bytearray(data)
    patched[PATCH_OFFSET:PATCH_OFFSET + 4] = REPLACEMENT
    if [i for i, (before, after) in enumerate(zip(data, patched)) if before != after] != [PATCH_OFFSET]:
        raise ValueError("Patch must alter exactly one byte")
    if source.resolve() == destination.resolve():
        raise ValueError("Destination must preserve the source file")
    destination.write_bytes(patched)
    print(f"source_sha256={SOURCE_SHA256}")
    print(f"patched_sha256={hashlib.sha256(patched).hexdigest()}")
    print(f"offset=0x{PATCH_OFFSET:x} instruction={ORIGINAL.hex()}->{REPLACEMENT.hex()}")
    print("bootmode=2 return=1->0; all other boot modes unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    patch_module(args.source, args.destination)
