#
# Copyright (C) 2022 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from Infinix-X6850 device
$(call inherit-product, device/infinix/X6850/device.mk)

# Inherit some common TWRP stuff.
$(call inherit-product, vendor/twrp/config/common.mk)

# Include TWRP props.
$(call inherit-product, device/infinix/X6850/twrp.mk)

# Include Fox props.
$(call inherit-product, device/infinix/X6850/fox.mk)

# Product Specifics
PRODUCT_NAME := twrp_X6850
PRODUCT_DEVICE := X6850
PRODUCT_BRAND := Infinix
PRODUCT_MODEL := Infinix NOTE 40 Pro
PRODUCT_MANUFACTURER := INFINIX

PRODUCT_GMS_CLIENTID_BASE := android-transsion

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="sys_mssi_64_64only_cn_armv82-user 16 BP2A.250605.031.A3 161334 release-keys"

BUILD_FINGERPRINT := Infinix/X6850-OP/Infinix-X6850:16/BP2A.250605.031.A3/301450016:user/release-keys

# Assert
TARGET_OTA_ASSERT_DEVICE := Infinix-X6850,X6850
