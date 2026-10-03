# WORK IN PROGRESS!

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
- [] Fasbootd
- [] Flashing
- [] MTP
- [] Sideload
- [] USB OTG
- [] Vibrator

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
git clone https://github.com/ardiandideyashidiq/recovery_device_infinix_X6850.git -b fox_14.1 ./device/infinix/X6850
```

Build:

```
source build/envsetup.sh
lunch twrp_X6850-ap2a-eng && mka adbd vendorbootimage
```