#!/bin/bash
# bt-switcher.sh — dynamic WiFi<->BT pin switcher for MX9Pro (RK3328, RTL8723BS)
# Requires: rk3328-mx9pro-v6.dtb as the booted base DTB, bt_enable.dtbo present.
#
# WHY THIS IS MORE THAN "wlan0 down/up":
# GPIO3_A4-A7 are physically shared between the WiFi SDIO host controller
# (mmc@ff5f0000) and UART1 (serial@ff120000). Bringing wlan0 down only stops
# IP traffic — it does NOT release the MMC controller's pinctrl claim on
# those pins. To actually free them we must unbind the MMC controller driver
# itself, and to make UART1 claim them we must force it through a fresh
# probe() (unbind+bind) AFTER the overlay updates its pinctrl-0 property,
# since pinctrl is bound once at probe time and does not re-apply on a live
# property change alone.

set -e

DTBO="/root/bt_enable.dtbo"
OVERLAY_DIR="/sys/kernel/config/device-tree/overlays/bt"
MMC_DEV="ff5f0000.dwmmc"
UART_DEV="ff120000.serial"
PIDFILE="/var/run/rtk_hciattach.pid"
BT_BAUD=1500000   # RTL8723BS BT firmware target baud (from original DTS max-speed)

log() { echo "[bt-switcher] $*"; }

find_driver() {
    # $1 = device name as it appears under /sys/bus/platform/devices/
    local dev="/sys/bus/platform/devices/$1"
    if [ ! -e "$dev/driver" ]; then
        echo ""
        return 1
    fi
    basename "$(readlink -f "$dev/driver")"
}

ensure_configfs() {
    if [ ! -d /sys/kernel/config/device-tree ]; then
        modprobe configfs 2>/dev/null || true
        mount -t configfs configfs /sys/kernel/config 2>/dev/null || true
    fi
}

start() {
    log "Switching GPIO3_A4-A7 from WiFi to Bluetooth..."

    # 1. Graceful network teardown first
    ip link set wlan0 down 2>/dev/null || true

    # 2. Unbind the WiFi SDIO host controller — THIS releases the pinctrl
    #    claim on the shared pins. Without this step the overlay below will
    #    either fail to apply cleanly or corrupt the live SDIO bus.
    MMC_DRV=$(find_driver "$MMC_DEV")
    if [ -z "$MMC_DRV" ]; then
        log "ERROR: $MMC_DEV has no bound driver — check device name with:"
        log "  ls /sys/bus/platform/devices/ | grep ff5f0000"
        exit 1
    fi
    log "Unbinding $MMC_DEV from driver $MMC_DRV..."
    echo "$MMC_DEV" > "/sys/bus/platform/drivers/$MMC_DRV/unbind"

    # 3. Load the overlay that adds UART1 pinctrl
    ensure_configfs
    mkdir -p "$OVERLAY_DIR"
    cat "$DTBO" > "$OVERLAY_DIR/dtbo"

    # 4. Force UART1 to re-probe so it picks up the NEW pinctrl-0 and
    #    actually calls pinctrl_select_state() to remux the physical pins.
    UART_DRV=$(find_driver "$UART_DEV")
    if [ -z "$UART_DRV" ]; then
        log "ERROR: $UART_DEV has no bound driver (base DTB may not have"
        log "uart1 status=okay — check with: cat /proc/device-tree/serial@ff120000/status)"
        exit 1
    fi
    log "Rebinding $UART_DEV (driver $UART_DRV) to apply new pinctrl..."
    echo "$UART_DEV" > "/sys/bus/platform/drivers/$UART_DRV/unbind"
    echo "$UART_DEV" > "/sys/bus/platform/drivers/$UART_DRV/bind"
    sleep 0.5

    # 5. Bring up the BT HCI UART transport
    log "Starting rtk_hciattach at ${BT_BAUD} baud..."
    rtk_hciattach -n -s "$BT_BAUD" ttyS1 rtk_h5 &
    echo $! > "$PIDFILE"
    log "Done. Check: hciconfig -a  /  dmesg | tail -20"
}

stop() {
    log "Switching GPIO3_A4-A7 back from Bluetooth to WiFi..."

    # 1. Stop the BT HCI attach process
    if [ -f "$PIDFILE" ]; then
        kill "$(cat "$PIDFILE")" 2>/dev/null || true
        rm -f "$PIDFILE"
    fi
    killall rtk_hciattach 2>/dev/null || true
    sleep 0.3

    # 2. Unbind UART1 — releases its pinctrl claim
    UART_DRV=$(find_driver "$UART_DEV")
    if [ -n "$UART_DRV" ]; then
        log "Unbinding $UART_DEV..."
        echo "$UART_DEV" > "/sys/bus/platform/drivers/$UART_DRV/unbind" 2>/dev/null || true
    fi

    # 3. Remove the overlay — live tree's uart1 node reverts to base state
    #    (no pinctrl-0 property at all)
    if [ -d "$OVERLAY_DIR" ]; then
        rmdir "$OVERLAY_DIR" 2>/dev/null || true
    fi

    # 4. Rebind UART1 in its pin-less state (keeps it present for next time)
    if [ -n "$UART_DRV" ]; then
        echo "$UART_DEV" > "/sys/bus/platform/drivers/$UART_DRV/bind" 2>/dev/null || true
    fi

    # 5. Rebind the WiFi SDIO host controller. This triggers a full re-probe:
    #    mmc-pwrseq toggles the chip reset-gpio (200ms settle, per DTS),
    #    SDIO bus re-enumerates, rtl8723bs re-loads firmware, wlan0
    #    reappears. This is NOT instant — allow several seconds.
    MMC_DRV=$(find_driver "$MMC_DEV")
    if [ -z "$MMC_DRV" ]; then
        # device may currently show no driver bound (from our earlier unbind) —
        # driver name doesn't change, so re-read via a known bound sibling or
        # just try the common rockchip dw-mshc driver name as fallback.
        MMC_DRV="rockchip_dw_mmc"
    fi
    log "Rebinding $MMC_DEV to driver $MMC_DRV..."
    echo "$MMC_DEV" > "/sys/bus/platform/drivers/$MMC_DRV/bind" 2>/dev/null || \
        log "WARNING: bind failed — check exact driver name: ls -l /sys/bus/platform/devices/$MMC_DEV/"

    log "Waiting for SDIO WiFi re-enumeration..."
    sleep 3

    ip link set wlan0 up 2>/dev/null || true
    # Most Armbian setups use NetworkManager — nudge it in case wlan0 is a
    # cold hotplug event it didn't auto-pick-up:
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
