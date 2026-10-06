#!/bin/bash
exec > /root/mx9diag.txt 2>&1
echo "=== uname ==="; uname -a
echo "=== armbianEnv ==="; cat /boot/armbianEnv.txt
echo "=== overlay-user ==="; ls -la /boot/overlay-user/
echo "=== dtb dir relevant ==="; ls -la /boot/dtb/rockchip/ | grep -iE "rk3318-box|rk3328-box|mx9"
echo "=== full dmesg to file ==="; dmesg > /root/mx9dmesg.txt; wc -l /root/mx9dmesg.txt
echo "=== mmc/sdio/wifi dmesg ==="; grep -iE "mmc|sdio|wifi|wlan|rtl|pwrseq|iodomain|io-domain|regulator" /root/mx9dmesg.txt | head -120
echo "=== gpio debug ==="; cat /sys/kernel/debug/gpio
echo "=== pinmux gpio3+ff5f0000 ==="; cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins | grep -E "gpio3|ff5f0000"
echo "=== regulators ==="; for r in /sys/class/regulator/regulator.*; do n=$(cat $r/name 2>/dev/null); u=$(cat $r/microvolts 2>/dev/null); s=$(cat $r/state 2>/dev/null); echo "$(basename $r): name=$n uv=$u state=$s"; done
echo "=== lsmod ==="; lsmod
echo "=== rfkill ==="; rfkill list 2>&1
echo "=== live tree dump ==="; dtc -I fs -O dts /proc/device-tree > /root/live-tree.dts 2>/root/live-tree.err; wc -l /root/live-tree.dts
echo "=== stock dtb dump ==="; dtc -I dtb -O dts /boot/dtb/rockchip/rk3318-box.dtb > /root/stock-rk3318-box.dts 2>/root/stock.err; wc -l /root/stock-rk3318-box.dts
echo "=== installed overlay dump ==="; dtc -I dtb -O dts /boot/overlay-user/mx9pro-board.dtbo > /root/installed-mx9pro-board.dts 2>&1; wc -l /root/installed-mx9pro-board.dts
echo "=== DONE ==="
