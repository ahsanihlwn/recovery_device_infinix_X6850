# Catatan native X6850B

## Penjelasan singkat

Bayangin PLATFORM sebagai pintu masuk pertama. Init dibuat dari source,
fstab kasih tahu partisi mana yang dipasang, dan modul kasih kernel driver yang
sesuai. Sesudah itu init pindah ke system; init vendor/ODM stock tetap jalan dari
partisinya. RECOVERY menyimpan OrangeFox. Dua bagian ini dirakit oleh build.

## Bahan yang dipakai

- Device asli: Infinix Note 40S, `X6850B`. Identitas dibaca dari `odm/etc/build.prop`.
- Firmware Android 16 `301450017`, SDK 36, patch `2026-08-01`.
- Image stock vendor_boot: SHA256 `e50692e0213f2bae96d62c608ebfbfed8af2f236afc2a9d8f00a61df00bdec42`.
- Header v4, page 4096, partisi 67108864 byte, fragmen PLATFORM + RECOVERY.
- DTB 183850 byte, SHA256 `c6a71e8dd261193acdf8d13838a6e906640dbe2c93cfc953360fb1c2747b7b85`; sama dengan X6850.
- Fstab PLATFORM SHA256 `69a673209393ed8c603bf52819dd7449ad6c4f3b1cf9ebcd17f08b0b24802c3d`; sama dengan X6850.
- Bootconfig dan seluruh alamat header sama dengan baseline.
- Footer stock diverifikasi hash-nya: AVB algorithm NONE, rollback index 0,
  location 0. Ini bukan bukti tanda tangan OEM dipercaya oleh bootloader.
- Kernel stock menerima ZSTD (`CONFIG_RD_ZSTD=y`).
- ODM DLKM diambil selektif dari payload dan hash hasilnya cocok dengan manifest.
  Ketiga driver touch sama dengan baseline; adaptive-ts recovery berbeda satu
  byte dari stock karena patch bootmode yang sudah ada.

- Layout init mentah identik dengan X6850: /init adalah symlink 16 byte ke
  /system/bin/init; ELF system/bin/init 3147960 byte dengan SHA256
  `37294eea3f55d67b623cdf89553c9d8edbb033d25ab624dc1597f4dc6668d530`.
  Native build memasang init first-stage statis hasil source pada /init.

## File yang disentuh

| File | Perubahan dan gunanya |
| --- | --- |
| BoardConfig.mk | Path, nama board, assert OTA menjadi X6850B; density menjadi 440. Geometri image dan bootstrap native tetap cocok dengan dump. |
| device.mk | Path produk menjadi device/infinix/X6850B; tetap memasukkan common native. |
| AndroidProducts.mk | Memilih twrp_X6850B.mk supaya lunch menemukan produk yang benar. |
| twrp_X6850.mk -> twrp_X6850B.mk | Nama produk, model dan inherit path diganti ke X6850B. |
| twrp.mk | Label versi recovery menjadi X6850B. |
| Android.mk | Guard TARGET_DEVICE memakai X6850B, sesuai PRODUCT_DEVICE. |
| vendorsetup.sh | FOX_BUILD_DEVICE dan label log menjadi X6850B; patch native dan installer full-image tetap aktif. |
| prebuilt/modules | Semua modul dan lima metadata dicocokkan dengan PLATFORM asli device ini. Replaces tc_hl7139a.ko with tc_sc8548_charger.ko. |
| prebuilt/source_vendor_boot.img | Referensi X6850 yang tidak dipakai build dihapus dari branch ini agar tidak disangka image stock X6850B. |
| tools/postprocess_vendor_boot.sh, tools/repack_vendor_boot.py | Dihapus setelah migrasi native; salinan hanya ada di arsip analisis lokal. |
| recovery/root/vendor/firmware/focaltech_ts_fw.bin | Diganti dengan bytes asli ODM X6850B; hash diperiksa sebelum build. |
| recovery/root/vendor/firmware/WMT_SOC.cfg | Diganti dengan bytes asli ODM X6850B; hash diperiksa sebelum build. |
| recovery/root/vendor/firmware/BT_FW.cfg | Diganti dengan bytes asli ODM X6850B; hash diperiksa sebelum build. |
| .gitattributes | BT_FW.cfg dan WMT_SOC.cfg diberi -text agar checkout Git menjaga bytes/CRLF stock, seperti aturan Conf_MultipleTest.ini yang sudah ada. |
| README.md | Perintah clone/lunch yang benar dan status uji X6850B. |
| docs/native-vendor16.md | Catatan ini. |

File modul/metadata yang berbeda dari X6850:

- `tc_sc8548_charger.ko`
- `tc_hl7139a.ko`
- `modules.alias`
- `modules.dep`
- `modules.load.recovery`

`modules.load` normal dan `modules.softdep` sama persis dengan baseline.
`modules.dep`, `modules.alias` dan `modules.load.recovery` diambil sebagai satu
paket dari device ini; urutan stock tidak dikarang ulang.

## File yang dipertahankan setelah diperiksa

Common bootstrap, patch 04, DTB, first-stage fstab, recovery fstab, init recovery,
konfigurasi Trustonic/FBE, shim, bootcontrol dan create_pl_dev
dipakai ulang. Firmware yang berbeda telah diganti dengan file ODM target seperti tabel di atas. Prop hardware yang khusus normal Android tetap berasal dari
vendor/ODM stock, bukan disalin ke recovery tanpa kebutuhan.

## Batas bukti

X6850 sudah melewati system_server pada pengujian sebelumnya. X6850B belum punya
bukti boot fisik, dekripsi atau tap/swipe. Driver dan input yang sama menguatkan
alasan memakai bootstrap yang sama, tetapi hasil runtime tetap harus diuji pada
unit X6850B dengan firmware/kernel yang cocok. Jangan flash image ini ke X6850.

## Hasil build bootstrap awal 2026-10-04 (historis, sebelum Enforcing)

- `lunch twrp_X6850B-ap2a-eng` dan `m -j16 adbd vendorbootimage` selesai, exit 0.
- Image 67108864 byte, SHA256 `9b4b81500bc1803f4afb77fa746c940726fc40a901d06aeea5145864d045a76f`.
- PLATFORM berisi 233 ko + 5 metadata, bytes cocok
  dengan stock target. Tidak ada ko dasar yang diduplikasi ke RECOVERY.
- Init first-stage ELF64 AArch64 statis tanpa PT_INTERP, cocok dengan hasil
  source build. SHA256 `d03b6eba42ffb23fb6ed9524d853c26df0f316a45be2e5bad6e126543c8dc150`.
- Dua fragmen ZSTD, header/DTB/fstab cocok dengan stock, root mount directories
  lengkap. Seluruh aset recovery/touch/firmware target cocok dengan source.
- Recovery product properties semuanya `X6850B`. BoardConfig mencatat density
  stock 440; ini bukan klaim uji DPI/UI fisik.
- Footer/hash AVB diverifikasi; image memakai algorithm NONE, rollback 0.
- ZIP SHA256 `ef8d49e786c410ed0ae3a1db406d597121006a0f22bfda6b82883e7dba8d2671`. `recovery.img` dalam ZIP sama persis
  dengan vendor_boot.img; CPIO recovery sama dengan fragmen RECOVERY native.
- Pengecekan shell, identitas source, input modul dan whitespace source lulus.
  Whitespace/CRLF firmware vendor dipertahankan sebagai data asli.
- Belum diuji pada perangkat fisik X6850B; belum ada bukti system_server, dekripsi
  atau tap/swipe target ini.


Catatan density: prop.default hasil build tidak memuat ro.sf.lcd_density.
Nilai TARGET_RECOVERY_DENSITY di BoardConfig mencatat nilai stock ODM dan
bukan bukti nilai DPI runtime. Layout/touch UI masih perlu diperiksa fisik.


## Utility touch pada tree native

Lihat [tools/README.md](../tools/README.md) untuk generator manual adaptive-ts.
Build memakai prebuilt touch yang telah diaudit; helper repack lama telah dihapus.
Patch 03 hanya dipakai untuk reverse hook installer lama saat setup native.
