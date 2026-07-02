echo "Enter fastboot mode first and download images by below command..."
REM echo "Erase Images:"
REM fastboot erase abl
REM fastboot erase adsp_oda
REM fastboot erase bluetooth
REM fastboot erase devcfg
REM fastboot erase dsp
REM fastboot erase hyp
REM fastboot erase imagefv
REM fastboot erase keymaster
REM fastboot erase logfs
REM fastboot erase modem
REM fastboot erase multiimgoem
REM fastboot erase qupfw
REM fastboot erase rpm
REM fastboot erase storsec
REM fastboot erase tz
REM fastboot erase uefisecapp
REM fastboot erase xbl
REM fastboot erase xbl_config

echo "Flash Slot A Non-HLOS Images:"
fastboot flash xbl_a xbl_s.melf
fastboot flash xbl_config_a xbl_config.elf
fastboot flash shrm_a shrm.elf
fastboot flash tz_a tz.mbn
fastboot flash aop_a aop.mbn
fastboot flash aop_config_a aop_devcfg.mbn
fastboot flash uefi_a uefi.elf
fastboot flash hyp_a hypvm.mbn
fastboot flash hyp_ac_config_a hyp_ac_config.mbn
fastboot flash keymaster_a keymint.mbn
fastboot flash modem_a NON-HLOS.bin
fastboot flash dsp_a dspso.bin
fastboot flash abl_a abl.elf
fastboot flash bluetooth_a BTFM.bin
fastboot flash xbl_ramdump_a XblRamdump.elf
fastboot flash imagefv_a imagefv.elf
fastboot flash uefisecapp_a uefi_sec.mbn
fastboot flash cpucp_a cpucp.elf
fastboot flash cpucp_dtb_a cpucp_dtbs.elf
fastboot flash dcp_a dcp.bin
fastboot flash devcfg_a devcfg_rfcomm.mbn
fastboot flash featenabler_a featenabler.mbn
fastboot flash qupfw_a qupv3fw.elf
fastboot flash apdp zeros_1sector.bin
fastboot flash toolsfv tools.fv
fastboot flash logfs logfs_ufs_8mb.bin

echo "Flash Slot B Non-HLOS Images:"
fastboot flash xbl_b xbl_s.melf
fastboot flash xbl_config_b xbl_config.elf
fastboot flash shrm_b shrm.elf
fastboot flash tz_b tz.mbn
fastboot flash aop_b aop.mbn
fastboot flash aop_config_b aop_devcfg.mbn
fastboot flash uefi_b uefi.elf
fastboot flash hyp_b hypvm.mbn
fastboot flash hyp_ac_config_b hyp_ac_config.mbn
fastboot flash keymaster_b keymint.mbn
fastboot flash modem_b NON-HLOS.bin
fastboot flash dsp_b dspso.bin
fastboot flash abl_b abl.elf
fastboot flash bluetooth_b BTFM.bin
fastboot flash xbl_ramdump_b XblRamdump.elf
fastboot flash imagefv_b imagefv.elf
fastboot flash uefisecapp_b uefi_sec.mbn
fastboot flash cpucp_b cpucp.elf
fastboot flash cpucp_dtb_b cpucp_dtbs.elf
fastboot flash dcp_b dcp.bin
fastboot flash devcfg_b devcfg_rfcomm.mbn
fastboot flash featenabler_b featenabler.mbn
fastboot flash qupfw_b qupv3fw.elf

echo "Flash Slot A HLOS Images:"
fastboot flash boot_a boot.img
fastboot flash recovery_a recovery.img
fastboot flash super super.img
fastboot flash vbmeta_system_a vbmeta_system.img
fastboot flash vendor_boot_a vendor_boot.img
fastboot flash metadata metadata.img
fastboot flash init_boot_a init_boot.img
fastboot flash dtbo_a dtbo.img
fastboot flash vbmeta_a vbmeta.img
fastboot flash storsec storsec.mbn
fastboot flash persist persist.img
fastboot flash userdata userdata.img

echo "Flash Slot B HLOS Images:"
fastboot flash boot_b boot.img
fastboot flash recovery_b recovery.img
fastboot flash vbmeta_system_b vbmeta_system.img
fastboot flash vendor_boot_b vendor_boot.img
fastboot flash init_boot_b init_boot.img
fastboot flash dtbo_b dtbo.img
fastboot flash vbmeta_b vbmeta.img

echo "Done..."
