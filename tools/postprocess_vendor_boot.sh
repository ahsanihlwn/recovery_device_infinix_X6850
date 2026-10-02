#!/bin/bash
set -euo pipefail

tools_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
device_dir="$(cd -- "${tools_dir}/.." && pwd)"
image="${1:?Missing vendor_boot image path}"
source_image="${FOX_X6850_STOCK_VENDOR_BOOT_IMAGE:-${device_dir}/prebuilt/source_vendor_boot.img}"
processor="${tools_dir}/repack_vendor_boot.py"

if [[ -n "${FOX_REFERENCE_VENDOR_BOOT_IMAGE:-}" ]]; then
    echo "[X6850] FOX_REFERENCE_VENDOR_BOOT_IMAGE conflicts with the vendor_boot postprocessor." >&2
    exit 1
fi

for required in "${image}" "${source_image}" "${processor}"; do
    if [[ ! -f "${required}" ]]; then
        echo "[X6850] Missing file: ${required}" >&2
        exit 1
    fi
done

exec python3 "${processor}" \
    --source "${source_image}" \
    --image "${image}" \
    --partition-size 67108864
