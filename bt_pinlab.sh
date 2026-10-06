#!/bin/bash
# Drive RTL8723BS control lines on the live box and probe the BT UART.
# Global line numbers: bank*32 + pin.
#   gpio3-8  (104) wifi_enable_h / chip REG_ON   -> HIGH = chip powered
#   gpio2-19 (83)  chip-en                      -> ?
#   gpio2-21 (85)  bt-dis                       -> LOW = BT section enabled
#   gpio2-15 (79)  host-wake-bt                 -> LOW
#   gpio2-16 (80)  bt-wake-host                 -> ?

set_pin() {           # $1=global line  $2=value 0/1
    local n=$1 v=$2
    [ -d /sys/class/gpio/gpio$n ] || echo $n > /sys/class/gpio/export 2>/dev/null
    local d=/sys/class/gpio/gpio$n
    if [ -d "$d" ]; then
        echo out > $d/direction 2>/dev/null
        echo $v  > $d/value 2>/dev/null
        printf "  gpio%-4s = %s (readback %s)\n" "$n" "$v" "$(cat $d/value 2>/dev/null)"
    else
        printf "  gpio%-4s = %s  EXPORT FAILED\n" "$n" "$v"
    fi
}

show_state() {
    echo "  --- current ---"
    for n in 104 83 85 79 80; do
        d=/sys/class/gpio/gpio$n
        if [ -d "$d" ]; then
            printf "  gpio%-4s dir=%s val=%s\n" "$n" "$(cat $d/direction 2>/dev/null)" "$(cat $d/value 2>/dev/null)"
        else
            printf "  gpio%-4s (not exported)\n" "$n"
        fi
    done
}

try_attach() {        # $1=baud  $2=protocol  $3=label
    echo "  --- rtk_hciattach baud=$1 proto=$2 ($3) ---"
    timeout 18 rtk_hciattach -n -s "$1" ttyS1 "$2" 2>&1 | \
        grep -viE 'resend' | head -8
}

echo "=== initial state ==="
show_state

echo
echo "=== driving combo A: chip high, bt-dis low, host-wake-bt low ==="
set_pin 104 1        # wifi_enable_h / REG_ON high
set_pin 83 1         # chip-en high
set_pin 85 0         # bt-dis low  (enable BT section)
set_pin 79 0         # host-wake-bt low
sleep 0.5
show_state

echo
try_attach 115200 rtk_h5 "H5"
try_attach 115200 rtk_h4 "H4"

echo
echo "=== combo B: chip high, chip-en low, bt-dis low ==="
set_pin 83 0
set_pin 104 1
sleep 0.5
try_attach 115200 rtk_h5 "H5"
try_attach 115200 rtk_h4 "H4"

echo
echo "=== combo C: chip high, bt-dis HIGH (module default) ==="
set_pin 104 1
set_pin 83 1
set_pin 85 1
sleep 0.5
try_attach 115200 rtk_h5 "H5"
try_attach 115200 rtk_h4 "H4"

echo
echo "=== combo D: chip high, chip-en low, bt-dis high ==="
set_pin 104 1
set_pin 83 0
set_pin 85 1
sleep 0.5
try_attach 115200 rtk_h5 "H5"
try_attach 115200 rtk_h4 "H4"

echo
echo "=== restore: chip powered via gpio3-8 high only ==="
set_pin 104 1
show_state
echo "DONE"