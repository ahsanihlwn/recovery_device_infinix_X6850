#!/usr/bin/env python3
"""Build X6850B vendor_boot from stock platform data and a recovery overlay."""

import argparse
import ctypes
import ctypes.util
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass

MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
LZ4_BLOCK_BYTES = 8 * 1024 * 1024
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
LZ4_LEGACY_MAGIC = b"\x02\x21\x4c\x18"


class RepackError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise RepackError(message)


def align(value, boundary):
    return (value + boundary - 1) // boundary * boundary


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def library(name):
    location = ctypes.util.find_library(name)
    require(location is not None, f"Missing native library: {name}")
    return ctypes.CDLL(location)


def decode_lz4_legacy(data):
    try:
        import lz4.block
    except ImportError:
        native = library("lz4")
        native.LZ4_decompress_safe.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int
        ]
        native.LZ4_decompress_safe.restype = ctypes.c_int

        def decode_block(block):
            destination = ctypes.create_string_buffer(LZ4_BLOCK_BYTES)
            count = native.LZ4_decompress_safe(
                block, destination, len(block), LZ4_BLOCK_BYTES
            )
            require(count >= 0, "Invalid legacy LZ4 block")
            return destination.raw[:count]
    else:
        def decode_block(block):
            return lz4.block.decompress(block, uncompressed_size=LZ4_BLOCK_BYTES)

    offset = 4
    output = bytearray()
    while offset < len(data):
        require(offset + 4 <= len(data), "Truncated legacy LZ4 block header")
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if count == 0:
            require(not any(data[offset:]), "Data after legacy LZ4 terminator")
            break
        require(count <= LZ4_BLOCK_BYTES + LZ4_BLOCK_BYTES // 255 + 16,
                "Invalid legacy LZ4 block size")
        require(offset + count <= len(data), "Truncated legacy LZ4 block")
        output.extend(decode_block(data[offset:offset + count]))
        require(len(output) <= MAX_ARCHIVE_BYTES, "LZ4 archive exceeds size limit")
        offset += count
    return bytes(output)


def decode_lz4_frame(data):
    try:
        import lz4.frame
    except ImportError:
        native = library("lz4")
        native.LZ4F_createDecompressionContext.argtypes = [
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint
        ]
        native.LZ4F_createDecompressionContext.restype = ctypes.c_size_t
        native.LZ4F_freeDecompressionContext.argtypes = [ctypes.c_void_p]
        native.LZ4F_freeDecompressionContext.restype = ctypes.c_size_t
        native.LZ4F_decompress.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p
        ]
        native.LZ4F_decompress.restype = ctypes.c_size_t
        native.LZ4F_isError.argtypes = [ctypes.c_size_t]
        native.LZ4F_isError.restype = ctypes.c_uint
        context = ctypes.c_void_p()
        status = native.LZ4F_createDecompressionContext(ctypes.byref(context), 100)
        require(not native.LZ4F_isError(status), "Cannot initialize LZ4 frame decoder")
        source = ctypes.create_string_buffer(data)
        offset = 0
        output = bytearray()
        try:
            while True:
                destination = ctypes.create_string_buffer(LZ4_BLOCK_BYTES)
                written = ctypes.c_size_t(LZ4_BLOCK_BYTES)
                consumed = ctypes.c_size_t(len(data) - offset)
                status = native.LZ4F_decompress(
                    context, destination, ctypes.byref(written),
                    ctypes.byref(source, offset), ctypes.byref(consumed), None
                )
                require(not native.LZ4F_isError(status), "Invalid LZ4 frame")
                output.extend(destination.raw[:written.value])
                offset += consumed.value
                require(len(output) <= MAX_ARCHIVE_BYTES, "LZ4 archive exceeds size limit")
                if status == 0:
                    require(not any(data[offset:]), "Data after LZ4 frame")
                    return bytes(output)
                require(consumed.value or written.value, "Truncated LZ4 frame")
        finally:
            native.LZ4F_freeDecompressionContext(context)
    else:
        return lz4.frame.decompress(data)


def zstd_codec(data, compress=False):
    try:
        from compression import zstd
    except ImportError:
        try:
            import zstandard
        except ImportError:
            native = library("zstd")
            native.ZSTD_isError.argtypes = [ctypes.c_size_t]
            native.ZSTD_isError.restype = ctypes.c_uint
            if compress:
                native.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
                native.ZSTD_compressBound.restype = ctypes.c_size_t
                capacity = native.ZSTD_compressBound(len(data))
                native.ZSTD_compress.argtypes = [
                    ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                    ctypes.c_size_t, ctypes.c_int
                ]
                native.ZSTD_compress.restype = ctypes.c_size_t
                destination = ctypes.create_string_buffer(capacity)
                count = native.ZSTD_compress(destination, capacity, data, len(data), 19)
            else:
                native.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                native.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
                capacity = native.ZSTD_getFrameContentSize(data, len(data))
                require(capacity <= MAX_ARCHIVE_BYTES,
                        "Invalid or unspecified ZSTD frame content size")
                native.ZSTD_decompress.argtypes = [
                    ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t
                ]
                native.ZSTD_decompress.restype = ctypes.c_size_t
                destination = ctypes.create_string_buffer(capacity)
                count = native.ZSTD_decompress(destination, capacity, data, len(data))
            require(not native.ZSTD_isError(count), "ZSTD codec failed")
            return destination.raw[:count]
        else:
            if compress:
                return zstandard.ZstdCompressor(level=19).compress(data)
            return zstandard.ZstdDecompressor().decompress(
                data, max_output_size=MAX_ARCHIVE_BYTES
            )
    else:
        return zstd.compress(data, level=19) if compress else zstd.decompress(data)


def decompress(data):
    if data.startswith(LZ4_LEGACY_MAGIC):
        decoded = decode_lz4_legacy(data)
    elif data.startswith(b"\x04\x22\x4d\x18"):
        decoded = decode_lz4_frame(data)
    elif data.startswith(ZSTD_MAGIC):
        decoded = zstd_codec(data)
    elif data.startswith(b"\x1f\x8b"):
        decoded = gzip.decompress(data)
    elif data.startswith((b"070701", b"070702")):
        decoded = data
    else:
        raise RepackError(f"Unsupported ramdisk magic: {data[:8].hex()}")
    require(len(decoded) <= MAX_ARCHIVE_BYTES, "Ramdisk exceeds archive size limit")
    return decoded


@dataclass
class CpioRecord:
    fields: tuple
    payload: bytes
    raw: bytes


def parse_cpio(data):
    offset = 0
    records = {}
    while True:
        require(offset + 110 <= len(data), "Truncated newc header")
        magic = data[offset:offset + 6]
        require(magic in (b"070701", b"070702"), "Ramdisk is not a newc archive")
        try:
            fields = tuple(int(data[offset + 6 + i * 8:offset + 14 + i * 8], 16)
                           for i in range(13))
        except ValueError as error:
            raise RepackError("Invalid newc header fields") from error
        namesize, filesize = fields[11], fields[6]
        require(namesize > 0, "Empty newc pathname")
        name_end = offset + 110 + namesize
        require(name_end <= len(data) and data[name_end - 1] == 0,
                "Truncated or unterminated newc pathname")
        raw_name = data[offset + 110:name_end - 1]
        require(b"\0" not in raw_name, "Embedded NUL in newc pathname")
        name = raw_name.decode("utf-8")
        payload_start = align(name_end, 4)
        payload_end = payload_start + filesize
        next_offset = align(payload_end, 4)
        require(next_offset <= len(data), f"Truncated newc entry: {name}")
        if name == "TRAILER!!!":
            require(filesize == 0 and not any(data[next_offset:]),
                    "Unexpected data after newc trailer")
            return records
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts,
                f"Unsafe newc pathname: {name}")
        name = str(path)
        require(name not in records, f"Duplicate newc pathname: {name}")
        kind = stat.S_IFMT(fields[1])
        require(fields[4] == 1 or kind == stat.S_IFDIR,
                f"Unsupported hardlink in newc archive: {name}")
        payload = data[payload_start:payload_end]
        if magic == b"070702":
            require(sum(payload) & 0xffffffff == fields[12],
                    f"Invalid newc checksum: {name}")
        records[name] = CpioRecord(fields, payload, data[offset:next_offset])
        offset = next_offset


def build_overlay(platform, recovery):
    records = []
    dropped = 0
    for name, record in recovery.items():
        previous = platform.get(name)
        if previous and record.payload == previous.payload and all(
                record.fields[index] == previous.fields[index]
                for index in (1, 2, 3, 9, 10)):
            dropped += 1
        else:
            records.append(record.raw)
    data = bytearray(b"".join(records))
    fields = (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 11, 0)
    data.extend(b"070701" + "".join(f"{field:08x}" for field in fields).encode()
                + b"TRAILER!!!\0")
    data.extend(bytes((-len(data)) % 512))
    return bytes(data), dropped


@dataclass
class Fragment:
    entry: bytes
    ramdisk_type: int
    name: str
    data: bytes


@dataclass
class VendorBoot:
    header: bytes
    page_size: int
    dtb: bytes
    bootconfig: bytes
    fragments: list
    payload_end: int


def validate_dtb(data):
    require(len(data) >= 40, "Missing or truncated DTB")
    if data[:4] == b"\xd0\x0d\xfe\xed":
        require(40 <= struct.unpack_from(">I", data, 4)[0] <= len(data),
                "Invalid flattened device tree size")
        return
    require(data[:4] == b"\xd7\xb7\xab\x1e" and len(data) >= 32,
            "Unsupported DTB container")
    _, total, header, entry_size, count, entries, _, version = struct.unpack_from(">8I", data)
    require(total == len(data) and header == 32 and entry_size >= 32 and count > 0
            and version == 0 and entries >= header and entries + count * entry_size <= total,
            "Invalid Android DT table")
    for index in range(count):
        size, offset = struct.unpack_from(">II", data, entries + index * entry_size)
        require(size >= 40 and offset >= entries + count * entry_size
                and offset + size <= total and data[offset:offset + 4] == b"\xd0\x0d\xfe\xed",
                "Invalid device tree inside Android DT table")
        require(40 <= struct.unpack_from(">I", data, offset + 4)[0] <= size,
                "Invalid embedded device tree size")


def parse_vendor_boot(data):
    require(len(data) >= 2128 and data[:8] == b"VNDRBOOT", "Not a vendor_boot image")
    version, page = struct.unpack_from("<II", data, 8)
    require(version == 4, "Only vendor_boot header version 4 is supported")
    require(page in (2048, 4096, 8192, 16384), "Invalid vendor_boot page size")
    rdsize = struct.unpack_from("<I", data, 24)[0]
    hsize, dsize = struct.unpack_from("<II", data, 2096)
    tsize, count, entrysize, csize = struct.unpack_from("<IIII", data, 2112)
    require(hsize == 2128 and entrysize == 108 and 0 < count <= 32,
            "Unsupported vendor_boot header/table layout")
    require(tsize == count * entrysize, "Vendor ramdisk table size mismatch")
    start = align(hsize, page)
    dtb_start = start + align(rdsize, page)
    table_start = dtb_start + align(dsize, page)
    config_start = table_start + align(tsize, page)
    end = config_start + align(csize, page)
    require(end <= len(data), "Truncated vendor_boot sections")
    validate_dtb(data[dtb_start:dtb_start + dsize])
    fragments = []
    consumed = 0
    names = set()
    for index in range(count):
        entry = data[table_start + index * entrysize:table_start + (index + 1) * entrysize]
        size, offset, rdtype = struct.unpack_from("<III", entry)
        require(offset == consumed and size > 0 and offset + size <= rdsize,
                "Overlapping, empty, or noncontiguous ramdisk fragments")
        require(rdtype in (0, 1, 2, 3), "Unknown vendor ramdisk type")
        name = entry[12:44].split(b"\0", 1)[0].decode("utf-8")
        require(name not in names, "Duplicate vendor ramdisk fragment name")
        names.add(name)
        fragments.append(Fragment(entry, rdtype, name,
                                  data[start + offset:start + offset + size]))
        consumed += size
    require(consumed == rdsize, "Unreferenced bytes in vendor ramdisk section")
    return VendorBoot(data[:start], page, data[dtb_start:dtb_start + dsize],
                      data[config_start:config_start + csize], fragments, end)


def single_fragment(image, kind):
    found = [fragment for fragment in image.fragments if fragment.ramdisk_type == kind]
    require(len(found) == 1, f"Expected exactly one ramdisk of type {kind}")
    return found[0]


def validate_platform(records):
    require(any(name.startswith("first_stage_ramdisk/fstab.") and record.payload
                for name, record in records.items()), "Stock platform has no first-stage fstab")
    modules = {PurePosixPath(name).name for name in records
               if name.startswith("lib/modules/") and name.endswith(".ko")}
    require(modules, "Stock platform has no kernel modules")
    for name, record in records.items():
        if name.startswith("lib/modules/") and name.endswith(".ko"):
            require(record.payload[:6] == b"\x7fELF\x02\x01" and len(record.payload) >= 64
                    and struct.unpack_from("<H", record.payload, 18)[0] == 183,
                    f"Kernel module is not AArch64 ELF: {name}")
    for filename in ("modules.load", "modules.load.recovery", "modules.dep"):
        record = records.get("lib/modules/" + filename)
        require(record is not None and record.payload, f"Stock platform has no {filename}")
        for line in record.payload.decode("utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            references = line.replace(":", " ").split()
            for reference in references:
                basename = PurePosixPath(reference).name
                if not basename.endswith(".ko"):
                    basename += ".ko"
                require(basename in modules, f"{filename} references a missing module: {reference}")


def source_avb(data, minimum_payload):
    require(data[-64:-60] == b"AVBf", "Stock reference has no AVB footer")
    _, major, minor, original_size, offset, size = struct.unpack_from(">4sIIQQQ", data, len(data) - 64)
    require(major == 1 and minor == 0 and minimum_payload <= original_size <= offset
            and offset + size <= len(data) - 64, "Invalid stock AVB footer")
    blob = data[offset:offset + size]
    require(len(blob) >= 256 and blob[:4] == b"AVB0", "Invalid stock vbmeta header")
    auth, auxiliary = struct.unpack_from(">QQ", blob, 12)
    algorithm = struct.unpack_from(">I", blob, 28)[0]
    descriptor_offset, descriptor_size = struct.unpack_from(">QQ", blob, 96)
    rollback, flags, location = struct.unpack_from(">QII", blob, 112)
    release = blob[128:176].split(b"\0", 1)[0].decode("utf-8")
    require(algorithm == 0 and auth == 0, "Stock reference must use AVB algorithm NONE")
    require(256 + auth + auxiliary <= len(blob)
            and descriptor_offset + descriptor_size <= auxiliary, "Invalid AVB descriptor range")
    descriptors = blob[256 + auth + descriptor_offset:
                       256 + auth + descriptor_offset + descriptor_size]
    properties = []
    hash_descriptor = None
    cursor = 0
    while cursor < len(descriptors):
        require(cursor + 16 <= len(descriptors), "Truncated AVB descriptor")
        tag, following = struct.unpack_from(">QQ", descriptors, cursor)
        require(following % 8 == 0 and cursor + 16 + following <= len(descriptors),
                "Invalid AVB descriptor length")
        entry = descriptors[cursor:cursor + 16 + following]
        if tag == 0:
            require(len(entry) >= 32, "Truncated AVB property")
            key_size, value_size = struct.unpack_from(">QQ", entry, 16)
            require(32 + key_size + value_size + 2 <= len(entry), "Truncated AVB property data")
            key = entry[32:32 + key_size].decode("utf-8")
            require(key and ":" not in key and "\0" not in key, "Unsupported AVB property key")
            require(entry[32 + key_size] == 0 and entry[33 + key_size + value_size] == 0,
                    "Invalid AVB property terminator")
            value = entry[33 + key_size:33 + key_size + value_size]
            properties.append((key, value))
        elif tag == 2:
            require(hash_descriptor is None and len(entry) >= 132, "Invalid AVB hash descriptors")
            image_size = struct.unpack_from(">Q", entry, 16)[0]
            hash_algorithm = entry[24:56].rstrip(b"\0").decode("ascii")
            name_size, salt_size, digest_size, hash_flags = struct.unpack_from(">IIII", entry, 56)
            require(132 + name_size + salt_size + digest_size <= len(entry), "Truncated AVB hash data")
            name = entry[132:132 + name_size].decode("utf-8")
            salt = entry[132 + name_size:132 + name_size + salt_size]
            digest = entry[132 + name_size + salt_size:
                           132 + name_size + salt_size + digest_size]
            require(name == "vendor_boot" and hash_algorithm == "sha256" and hash_flags in (0, 1),
                    "Unsupported stock AVB hash descriptor")
            require(image_size == original_size and digest_size == 32
                    and hashlib.sha256(salt + data[:image_size]).digest() == digest,
                    "Stock AVB hash does not match its image")
            hash_descriptor = (salt, hash_flags)
        else:
            raise RepackError(f"Unsupported stock AVB descriptor type: {tag}")
        cursor += len(entry)
    require(hash_descriptor is not None, "Stock AVB has no vendor_boot hash descriptor")
    return dict(salt=hash_descriptor[0], hash_flags=hash_descriptor[1], properties=properties,
                rollback=rollback, flags=flags, location=location, release=release)


def assemble(source, compressed):
    header = bytearray(source.header)
    ramdisks = bytearray()
    table = bytearray()
    for fragment, data in zip(source.fragments, compressed):
        entry = bytearray(fragment.entry)
        struct.pack_into("<II", entry, 0, len(data), len(ramdisks))
        table.extend(entry)
        ramdisks.extend(data)
    struct.pack_into("<I", header, 24, len(ramdisks))
    output = bytearray(header)
    for section in (ramdisks, source.dtb, table, source.bootconfig):
        output.extend(section)
        output.extend(bytes((-len(output)) % source.page_size))
    return bytes(output)


def avb_command(avbtool, command, *arguments):
    result = subprocess.run([sys.executable, str(avbtool), command, *map(str, arguments)],
                            check=False, capture_output=True, text=True)
    require(result.returncode == 0,
            f"avbtool {command} failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout


def add_footer(image, avbtool, metadata, partition_size, temporary):
    arguments = ["--image", image, "--partition_size", partition_size,
                 "--partition_name", "vendor_boot", "--algorithm", "NONE",
                 "--hash_algorithm", "sha256", "--salt", metadata["salt"].hex(),
                 "--rollback_index", metadata["rollback"], "--flags", metadata["flags"],
                 "--rollback_index_location", metadata["location"],
                 "--internal_release_string", metadata["release"]]
    if metadata["hash_flags"] & 1:
        arguments.append("--do_not_use_ab")
    for index, (key, value) in enumerate(metadata["properties"]):
        property_file = temporary / f"property-{index}.bin"
        property_file.write_bytes(value)
        arguments.extend(["--prop_from_file", f"{key}:{property_file}"])
    avb_command(avbtool, "add_hash_footer", *arguments)
    avb_command(avbtool, "verify_image", "--image", image)


def replace_atomically(output, data, mode):
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".recovery-", dir=output.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def run(args):
    image_path = args.image.resolve()
    output = (args.output or args.image).resolve()
    image_data = image_path.read_bytes()
    generated = parse_vendor_boot(image_data)
    recovery_data = decompress(single_fragment(generated, 2).data)
    recovery = parse_cpio(recovery_data)
    require(recovery, "Recovery ramdisk is empty")
    if args.extract_recovery:
        require(args.output is not None, "--extract-recovery requires --output")
        require(output != image_path, "Extraction output must differ from the image")
        replace_atomically(output, recovery_data, 0o644)
        print(json.dumps(dict(recovery_cpio_bytes=len(recovery_data),
                              recovery_cpio_sha256=sha256(recovery_data))))
        return
    require(args.source is not None, "Repacking requires --source")
    source_path = args.source.resolve()
    require(output != source_path, "Output must not overwrite the stock reference")
    source_data = source_path.read_bytes()
    source = parse_vendor_boot(source_data)
    require(len(source.fragments) == 2, "Stock reference must contain platform and recovery only")
    platform_fragment = single_fragment(source, 1)
    single_fragment(source, 2)
    require(source.dtb == generated.dtb, "Generated DTB differs from the stock reference")
    require(args.partition_size > 65536 and args.partition_size % source.page_size == 0,
            "Invalid partition size")
    require(len(source_data) == args.partition_size, "Stock reference size differs from the partition")
    platform_data = decompress(platform_fragment.data)
    platform = parse_cpio(platform_data)
    validate_platform(platform)
    require(any(name in recovery and recovery[name].payload
                for name in ("system/bin/recovery", "sbin/recovery")), "Recovery binary is missing")
    metadata = source_avb(source_data, source.payload_end)
    overlay_data, dropped = build_overlay(platform, recovery)
    overlay = parse_cpio(overlay_data)
    compressed_platform = zstd_codec(platform_data, compress=True)
    compressed_overlay = zstd_codec(overlay_data, compress=True)
    require(decompress(compressed_platform) == platform_data
            and decompress(compressed_overlay) == overlay_data, "ZSTD round-trip verification failed")
    compressed = [compressed_platform if fragment.ramdisk_type == 1 else compressed_overlay
                  for fragment in source.fragments]
    payload = assemble(source, compressed)
    require(len(payload) <= args.partition_size - 65536,
            f"vendor_boot payload {len(payload)} exceeds AVB limit {args.partition_size - 65536}")
    default_avbtool = Path(__file__).resolve().parents[4] / "external/avb/avbtool.py"
    avbtool = (args.avbtool or default_avbtool).resolve()
    require(avbtool.is_file(), f"Missing avbtool: {avbtool}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".vendor-boot-", dir=output.parent) as directory:
        temporary = Path(directory)
        candidate = temporary / "vendor_boot.img"
        candidate.write_bytes(payload)
        add_footer(candidate, avbtool, metadata, args.partition_size, temporary)
        final_data = candidate.read_bytes()
        require(len(final_data) == args.partition_size, "AVB produced an unexpected partition size")
        final = parse_vendor_boot(final_data)
        require(decompress(single_fragment(final, 1).data) == platform_data,
                "Final platform archive differs from stock")
        require(decompress(single_fragment(final, 2).data) == overlay_data,
                "Final recovery archive differs from its overlay")
        require(final.dtb == source.dtb and final.bootconfig == source.bootconfig,
                "Final DTB or bootconfig differs from stock")
        source_avb(final_data, final.payload_end)
        os.chmod(candidate, stat.S_IMODE(image_path.stat().st_mode))
        os.replace(candidate, output)
    print(json.dumps(dict(
        output=str(output), partition_bytes=len(final_data), payload_bytes=len(payload),
        platform_cpio_sha256=sha256(platform_data), platform_zstd_bytes=len(compressed_platform),
        recovery_cpio_sha256=sha256(overlay_data), recovery_zstd_bytes=len(compressed_overlay),
        dropped_identical=dropped, overlay_entries=len(overlay), dtb_sha256=sha256(source.dtb),
        image_sha256=sha256(final_data), avb_algorithm="NONE", avb_hash_algorithm="sha256"
    ), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Stock vendor_boot reference image")
    parser.add_argument("--image", type=Path, required=True, help="Generated vendor_boot image")
    parser.add_argument("--partition-size", type=int, default=67108864)
    parser.add_argument("--output", type=Path, help="Output path; defaults to replacing --image")
    parser.add_argument("--avbtool", type=Path, help="Path to the AOSP avbtool.py")
    parser.add_argument("--extract-recovery", action="store_true",
                        help="Extract an uncompressed recovery cpio instead of repacking")
    args = parser.parse_args()
    try:
        run(args)
    except (RepackError, OSError, ValueError, struct.error, UnicodeError) as error:
        parser.exit(1, f"[X6850B] {error}\n")


if __name__ == "__main__":
    main()
