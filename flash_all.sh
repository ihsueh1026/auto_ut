#!/bin/bash
#
# Program: "flash_sw6100.sh"
#   Flash the images of SW6100 platform.
#
# Version:
#   0.1
#
# Author:
#   Abel, Fang
#
# History:
#   Abel20260513: v0.1. Initial.
#

#Settings
SCRIPT_VERSION='0.1'
SCRIPT_NAME=$(basename $0)
SCRIPT_DIR=$(dirname $0)
FIGLET_WIDTH=100

# Define Fastboot command prefix
FASTBOOT_CMD="fastboot"

# The XML defined images and partitions for flash process
XML_FILE='rawprogram0.xml'
# The partition table image
PTABLE_IMAGE='gpt_both0.bin'
# The partition table parition
PTABLE_PARTITION='partition:0'

# Define if erase before flash image
ERASE_BEFORE_FLASH=0
# Define if fastboot update <DOU_ZIP>, will be set new value via input parameter
DOU_UPDATE="0"
# Define only flash XXX_a partition of A/B partition, will be set new value via input parameter
FLASH_A_ONLY=0
# Define if erase parition
FLASH_PARTITION=0

# Inditicate whether images to be flashed is not exist.
IMAGE_NOT_FOUND='false'

# Create an 'exclude list' for flash image
EXCLUDE_LIST=("PrimaryGPT" "BackupGPT" "gpt_main0" "gpt_backup0")


#------------------------------------------------------------------------------------------------------------
# Func: figletAdv
# Desc: Print the message using figlet if it is installed; otherwise, use echo.
#------------------------------------------------------------------------------------------------------------
function figletAdv(){
    if [ -z "${1}" ]; then
        # : (a colon)
        #   Do nothing beyond expanding arguments and performing redirections.
        #   The return status is zero. Do nothing
        :
    else
        # Check if the figlet utility is registered in the shell hash table.
        if hash figlet 2>/dev/null; then
            figlet -w ${FIGLET_WIDTH} ${1}
        else
            echo
            echo "${1}!!!"
            echo
        fi
    fi
}


#------------------------------------------------------------------------------------------------------------
# Func: show_help
# Desc: Print help message
#------------------------------------------------------------------------------------------------------------
show_help() {
    cat << EOF

<< SW6100 auto flash tool >>

Usage: ${SCRIPT_NAME} [OPTIONS]

OPTIONS:
  ""            (Default) flash all Slot A/B image.
  -a            Flash Slot A only
  -e            Erase beofre flash
  -p            (TBD) Flash partition table first and flash all images.
  -w            (TBD) Flash DOU zip (fastboot update)
  -h            Show this help

e.g.
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} -a

Revision: ${SCRIPT_VERSION}
EOF
}


#------------------------------------------------------------------------------------------------------------
# Func: check_parameters
# Desc: Check the input parameters and show help when needed.
#------------------------------------------------------------------------------------------------------------
function check_parameters(){
    echo "==> ${FUNCNAME[0]}"

    # Use getopts inside the function to process passed arguments
    # Note: OPTIND must be reset to 1 inside functions
    local OPTIND
    OPTIND=1

    while getopts "aehpw:" opt; do
#        echo "Debug: opt=$opt, OPTARG=$OPTARG, OPTIND=$OPTIND"
        case $opt in
            a)
                FLASH_A_ONLY=1
                ;;
            h)
                show_help
                exit 0
                ;;
            e)
                ERASE_BEFORE_FLASH=1
                echo 'Set as "Erase Before Flash"'
                ;;
            p)
                echo "-p: TBD"
                exit 0
#                FLASH_PARTITION=1
#                ERASE_BEFORE_FLASH=0
                ;;
            w)
                echo "-w: TBD"
                DOU_UPDATE="1"
                exit 0
                ;;
            \?)
                echo "Invalid option"
                exit 1
                ;;
        esac
    done

    # Check if there are leftover unparsed parameters
    shift $((OPTIND - 1))
    if [ "$#" -gt 0 ]; then
        echo "Error：Unsupported parameter format '$1'. All parameter must start with a '-'"
        show_help
        exit 1
    fi

    if [ "${FLASH_A_ONLY}" == "1" ]; then
        echo -e "Set as \"Flash Slot A only\"\n"
    else
        echo -e "Set as \"Flash slot A/B\"\n"
    fi
}


#------------------------------------------------------------------------------------------------------------
# Func: check_battery_level
# Desc: Check battery level
#------------------------------------------------------------------------------------------------------------
# 檢查電量函數 / Battery level check function
check_battery_level() {
    echo "==> ${FUNCNAME[0]}"

    local -r battery_ok=$(fastboot getvar battery-soc-ok 2>&1 | grep "battery-soc-ok" | cut -d: -f2 | tr -d ' ')

    if [ "$battery_ok" != "yes" ]; then
        figletAdv "Battery Too Low"
        echo "Warning: Battery level too low (${battery_ok}); flashing success cannot be guaranteed."
        # Do "fastboot oem off-mode-charge 0" for by pass internal battery check
        echo "Please connect the charger or execute the force-power command (if supported by your platform)."
        exit 1
    fi
}


#------------------------------------------------------------------------------------------------------------
# Func: check_files
# Desc: Check whether all images to flash are exist, or set IMAGE_NOT_FOUND as true.
#------------------------------------------------------------------------------------------------------------
function check_files(){
    echo "==> ${FUNCNAME[0]}"

    local not_found='false'

    if [ -f ${XML_FILE} ]; then
        local images=$(xmllint --xpath "//program[@filename != '']/@filename" "${XML_FILE}")

        for entry in ${images}; do
            # Extract the 2nd part using quote as delimiter
            file_name=$(echo "$entry" | cut -d'"' -f2)

            if [ ! -f "${file_name}" ]; then
                IMAGE_NOT_FOUND='true'
                echo -e "The ${file_name} is not found\n"
            fi
        done
    else
        figletAdv "Missing rawprogram0.xml"
        echo "Please copy \"non_hlos/common/build/emmc/rawprogram0.xml\" here"
        exit 1
    fi

    if [ "${IMAGE_NOT_FOUND}" = 'true' ]; then
        figletAdv "Missing images"
        exit 1
    else
        echo -e "OK\n"
    fi

    if [ "${FLASH_PARTITION}" == "1" ] && [ ! -f ${PTABLE_IMAGE} ] ; then
        figletAdv "Missing ${PTABLE_IMAGE}"
        echo -e "The ${PTABLE_IMAGE} is not found\n"
        exit 1
    fi
}


#------------------------------------------------------------------------------------------------------------
# Func: check_fastboot_access
# Desc: Determine whether to use sudo mode based on fastboot permissions.
#------------------------------------------------------------------------------------------------------------
function check_fastboot_access(){
    echo "==> ${FUNCNAME[0]}"

    #Detect if sudo-free access is available
    if fastboot devices 2>&1 | grep -q "no permissions"; then
        echo -e "Permissions denied, switching to sudo mode...\n"
        FASTBOOT_CMD="sudo fastboot"
    else
        echo -e "Normal mode\n"
    fi
}


#------------------------------------------------------------------------------------------------------------
# Func: flash_subRoutine
# Desc: Simplified the fastboot flashing process (include erasing before flashiing, using sudo or not using sudo,,,etc)
#------------------------------------------------------------------------------------------------------------
function flash_subRoutine(){
    local targetPartition=${1}
    local sourceImage=${2}

    if [ "${targetPartition}" == "system" ]; then
        if [ "${ERASE_BEFORE_FLASH}" == "1" ]; then
            echo
            echo "==> ${FASTBOOT_CMD} erase system"
            ${FASTBOOT_CMD} erase system
        fi
        echo "==> ${FASTBOOT_CMD} flash -S 200M ${targetPartition} ${sourceImage}"
        ${FASTBOOT_CMD} flash -S 200M ${targetPartition} ${sourceImage}
    elif [ "${DOU_UPDATE}" == "true" ]; then
        echo "==> ${FASTBOOT_CMD} update ${targetPartition} -w"
        # "-w" will erase userdata and metadata.
        ${FASTBOOT_CMD} update ${targetPartition} -w
    else
        if [ "${ERASE_BEFORE_FLASH}" == "1" ]; then
            echo
            echo "==> ${FASTBOOT_CMD} erase ${targetPartition}"
            ${FASTBOOT_CMD} erase ${targetPartition}
        fi
        echo "==> ${FASTBOOT_CMD} flash ${targetPartition} ${sourceImage}"
        ${FASTBOOT_CMD} flash ${targetPartition} ${sourceImage}
    fi

    local varErrorCode=$(echo $?)
    if [ "${varErrorCode}" != 0 ]; then
        echo "=====      The ${targetPartition} flash failed(${varErrorCode})!     ====="
        exit ${varErrorCode}
    fi
}


#------------------------------------------------------------------------------------------------------------
# Func: erase_subRoutine
# Desc: Simplified the fastboot erase process (using sudo or not using sudo)
#------------------------------------------------------------------------------------------------------------
function erase_subRoutine(){
    local targetPartition=${1}

    echo "==> ${FASTBOOT_CMD} erase ${targetPartition}"
    ${FASTBOOT_CMD} erase ${targetPartition}
    echo
}


#------------------------------------------------------------------------------------------------------------
# Func: script_main
# Desc: The major fastboot flash process
#------------------------------------------------------------------------------------------------------------
function script_main (){
    check_parameters "$@"
#    check_battery_level
    check_files

    check_fastboot_access

    echo "==> ${FASTBOOT_CMD} getvar version-bootloader"
    ${FASTBOOT_CMD} getvar version-bootloader
    echo

#   echo "DBG: Check Input"; exit 0

    # Flash partition table
    if [ "${FLASH_PARTITION}" == "1" ]; then
#        erase_subRoutine {PTABLE_PARTITION}
        echo "==> GPT table is flashing ...."
        flash_subRoutine ${PTABLE_PARTITION} ${PTABLE_IMAGE}
        fastboot reboot-bootloader
        sleep 5
    fi

    # Flash parition based on ${XML_FILE}
    while IFS= read -r line; do
        # Extract label and filename from each line
        targetLabel=$(echo "$line" | sed -n 's/.*label="\([^"]*\)".*/\1/p')
        targetFile=$(echo "$line" | sed -n 's/.*filename="\([^"]*\)".*/\1/p')

        if [[ -n "${targetLabel}"  &&  -n "${targetFile}" ]]; then
            if [[ ! " ${EXCLUDE_LIST[@]} " =~ " ${targetLabel} " ]]; then
                if [[ "${FLASH_A_ONLY}" == "1" && "${targetLabel}" =~ _b$ ]]; then
                    echo -e "==> Skip ${targetLabel} partition\n"
                else
                    flash_subRoutine ${targetLabel} ${targetFile}
                    echo
                fi
            else
                echo -e "==> Skip ${targetLabel} partition\n"
            fi
        fi
    done < <(xmllint --xpath "//program[@filename != '']" "${XML_FILE}" | sed 's/><\/program>/ /g')

    if [ ${FLASH_A_ONLY} = "1" ]; then
        # Set active slot as A
        echo
        echo "==> ${FASTBOOT_CMD} getvar current-slot"
#        ${FASTBOOT_CMD} getvar current-slot
        echo "==> ${FASTBOOT_CMD} --set-active=a"
#        ${FASTBOOT_CMD} --set-active=a
        echo
    fi

    echo "#####     FLASH IMAGE DONE!!!     #####"
    echo; date +"%Y.%m.%d. %k:%M:%S"
    exit 0
}


# The entry point
script_main "$@"
