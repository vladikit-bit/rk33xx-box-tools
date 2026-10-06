#!/bin/bash
# bt-switcher.sh (v7) — WiFi<->BT pin switcher for MX9Pro (RK3328, RTL8723BS)
# Requires: rk3328-mx9pro-v7.dtb as the booted base DTB, bt_enable.dtbo present.
#
# v7 CHANGE FROM EARLIER VERSIONS:
# The combo chip's shared enable line (GPIO3_B0) is now an always-on
# gpio-hog in the base DTB, asserted once at kernel boot. It is NO LONGER
# tied to mmc@ff5f0000's bind/unbind lifecycle (that was the actual root
# cause of the H5 sync timeouts: unbinding the MMC host used to trigger
# mmc-pwrseq's power_off(), which cut power to the WHOLE chip -- including
# the BT front-end -- before rtk_hciattach ever got a chance to talk to it).
# This script now ONLY handles pin muxing, nothing about chip power.
#
# Exact device/driver names below were confirmed live on this box:
#   MMC device : ff5f0000.mmc   (NOT ff5f0000.dwmmc)
#   MMC driver : dwmmc_rockchip
#   UART device: ff120000.serial
#   UART driver: dw-apb-uart

set -e

DTBO="/root/bt_enable.dtbo"
OVERLAY_DIR="/sys/kernel/config/device-tree/overlays/bt"
MMC_DEV="ff5f0000.mmc"
MMC_DRV_FALLBACK="dwmmc_rockchip"
UART_DEV="ff120000.serial"
PIDFILE="/var/run/rtk_hciattach.pid"
BT_BAUD="115200"   # try rtk_h5 first; if it still fails, test rtk_h4 manually

log() { echo "[bt-switcher] $1"; }

find_driver() {
    local dev="/sys/bus/platform/devices/$1"
    if [ ! -e "$dev/driver" ]; then
        echo ""
        return 0
    fi
    basename "$(readlink -f "$dev/driver")"
}

ensure_configfs() {
    mkdir -p /sys/kernel/config 2>/dev/null || true
    mount -t configfs none /sys/kernel/config 2>/dev/null || true
}

start() {
    log "Switching GPIO3_A4-A7 from WiFi to Bluetooth (chip stays powered)..."

    rfkill unblock bluetooth 2>/dev/null || true

    ip link set wlan0 down 2>/dev/null || true

    MMC_DRV=$(find_driver "$MMC_DEV")
    if [ -n "$MMC_DRV" ]; then
        log "Unbinding $MMC_DEV from driver $MMC_DRV..."
        echo "$MMC_DEV" > "/sys/bus/platform/drivers/$MMC_DRV/unbind"
    else
        log "NOTE: $MMC_DEV already unbound."
    fi

    ensure_configfs
    mkdir -p "$OVERLAY_DIR"
    cat "$DTBO" > "$OVERLAY_DIR/dtbo"

    UART_DRV=$(find_driver "$UART_DEV")
    if [ -z "$UART_DRV" ]; then
        log "ERROR: $UART_DEV has no bound driver. Check:"
        log "  cat /proc/device-tree/serial@ff120000/status"
        exit 1
    fi
    log "Rebinding $UART_DEV (driver $UART_DRV) to apply new pinctrl..."
    echo "$UART_DEV" > "/sys/bus/platform/drivers/$UART_DRV/unbind"
    echo "$UART_DEV" > "/sys/bus/platform/drivers/$UART_DRV/bind"
    sleep 0.5

    log "Starting rtk_hciattach (H5, ${BT_BAUD} baud)..."
    rtk_hciattach -n -s "$BT_BAUD" ttyS1 rtk_h5 &
    echo $! > "$PIDFILE"
    log "Done. Check: hciconfig -a  /  dmesg | tail -20"
    log "If H5 still times out, try manually: rtk_hciattach -n -s $BT_BAUD ttyS1 rtk_h4"
}

stop() {
    log "Switching GPIO3_A4-A7 back from Bluetooth to WiFi..."

    if [ -f "$PIDFILE" ]; then
        kill "$(cat "$PIDFILE")" 2>/dev/null || true
        rm -f "$PIDFILE"
    fi
    killall rtk_hciattach 2>/dev/null || true
    sleep 0.3

    UART_DRV=$(find_driver "$UART_DEV")
    if [ -n "$UART_DRV" ]; then
        log "Unbinding $UART_DEV..."
        echo "$UART_DEV" > "/sys/bus/platform/drivers/$UART_DRV/unbind" 2>/dev/null || true
    fi

    if [ -d "$OVERLAY_DIR" ]; then
        rmdir "$OVERLAY_DIR" 2>/dev/null || true
    fi

    # Chip was never powered off this whole time (gpio-hog keeps it enabled),
    # so this rebind is a soft SDIO re-detect, not a full power-cycle.
    MMC_DRV=$(find_driver "$MMC_DEV")
    [ -z "$MMC_DRV" ] && MMC_DRV="$MMC_DRV_FALLBACK"
    log "Rebinding $MMC_DEV to driver $MMC_DRV..."
    echo "$MMC_DEV" > "/sys/bus/platform/drivers/$MMC_DRV/bind" 2>/dev/null || \
        log "WARNING: bind failed — check: ls -l /sys/bus/platform/devices/$MMC_DEV/"

    log "Waiting for SDIO WiFi re-enumeration..."
    sleep 2

    ip link set wlan0 up 2>/dev/null || true
    nmcli device connect wlan0 2>/dev/null || true

    log "Done. Check: ip link show wlan0  /  nmcli device status"
}

case "$1" in
    start) start ;;
    stop) stop ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac
