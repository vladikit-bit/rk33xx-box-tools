# RK33xx box tools — BT/UART/GPIO reverse engineering on RK3318/RK3328 TV boxes

Tools and captures from researching Android TV boxes **MX9 Pro (RK3328)** and an **RK3318 box** running Armbian (October 2026). Goal: switching the WiFi↔Bluetooth pin-mux, enabling UART0, auditing pin configuration and dumping the live device tree.

**Scripts:** `bt_pinlab*.sh` (BT pin-mux lab), `diag.sh`, `dtsdiff.py`, `iomux_decode.py`, `pin_idle_scan.py`, `pincfg_audit.py`, `make_bt_mode*.py`, `enable_uart0.py`.

**Kernel RE (annotated copies):** `gp.c`, `gpiolib.c`, `mmc_core.c`, `pwrseq_simple.c` etc. — Rockchip GPIO/pinctrl/mmc driver chains, read to understand the mux logic.

**DTS / diagnostics:** `mx9pro-board.dts`, live and stock device trees, dmesg/diag captures, GRF register dumps.

**`root-` files:** `bt-switcher.sh` / `bt-switcher-v7.sh` (final WiFi↔BT GPIO pin-mux switcher for MX9 Pro / RTL8723BS), `bt_enable.dtbo` overlay, compiled DTBs v6/v7.

**Related:** [projector-research](https://github.com/vladikit-bit/projector-research) — same author.
