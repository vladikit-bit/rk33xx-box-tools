#!/bin/bash
# Sweep RTL8723BS BT control-pin combinations with the chip ACTUALLY powered.
# Precondition: sdio-pwrseq released, gpio104 exported and driven high.

chip_power() {
    local d=/sys/class/gpio/gpio104
    [ -d "$d" ] || { echo 104 > /sys/class/gpio/export 2>/dev/null; }
    d=/sys/class/gpio/gpio104
    echo out > $d/direction 2>/dev/null
    echo 1   > $d/value 2>/dev/null
}

set_pin() {
    local n=$1 v=$2 d=/sys/class/gpio/gpio$n
    [ -d "$d" ] || echo $n > /sys/class/gpio/export 2>/dev/null
    d=/sys/class/gpio/gpio$n
    [ -d "$d" ] || return 1
    echo out > $d/direction 2>/dev/null
    echo $v   > $d/value 2>/dev/null
}

try() {   # $1=baud $2=proto
    local out
    out=$(timeout 15 rtk_hciattach -n -s "$1" ttyS1 "$2" 2>&1 | grep -viE 'resend|^$')
    if echo "$out" | grep -qiE 'signature error|timed out|Load FW OK'; then
        if echo "$out" | grep -qi 'Load FW OK'; then
            echo "    [$1/$2] FW SENT -> $(echo "$out" | grep -iE 'signature|timed out' | head -1)"
        else
            echo "    [$1/$2] no response (timeout)"
        fi
    else
        echo "    [$1/$2] *** $(echo "$out" | grep -viE 'hciattach version|init uart' | head -2 | tr '\n' ' ')"
    fi
}

combo() {  # $1=label $2=chip-en $3=bt-dis $4=host-wake-bt
    echo "=== $1 (chip-en=$2 bt-dis=$3 host-wake-bt=$4) ==="
    chip_power
    set_pin 83 $2
    set_pin 85 $3
    set_pin 79 $4
    sleep 0.4
    try 115200 rtk_h5
    try 115200 rtk_h4
}

combo "A: en=HIGH dis=LOW  wake=LOW"  1 0 0
combo "B: en=LOW  dis=LOW  wake=LOW"  0 0 0
combo "C: en=HIGH dis=HIGH wake=LOW"  1 1 0
combo "D: en=LOW  dis=HIGH wake=LOW"  0 1 0
combo "E: en=HIGH dis=LOW  wake=HIGH" 1 0 1
combo "F: en=LOW  dis=LOW  wake=HIGH" 0 0 1

echo
echo "=== final: chip-en LOW, bt-dis LOW (typical rtl8723bs idle) ==="
chip_power; set_pin 83 0; set_pin 85 0; set_pin 79 0
try 115200 rtk_h5
try 1500000 rtk_h5
try 115200 rtk_h4
echo DONE