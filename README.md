# RK33xx box tools — реверс BT/UART/GPIO на RK3318/RK3328 TV-box'ах

Інструменти й дампи дослідження Android TV-box **MX9 Pro (RK3328)** та **RK3318 box** на Armbian (жовтень 2026). Мета — перемикання пін-муксу WiFi↔Bluetooth, увімкнення UART0, аудит pin-cfg і живе дерево пристроїв.

## Зміст (з `firmware_temp\Армбіан_ха\`)

**Скрипти-інструменти:**
| Файл | Що робить |
|---|---|
| `bt_pinlab.sh`, `bt_pinlab2.sh` | лабораторія BT-пінів (іOMUX перемикання) |
| `diag.sh` | швидка діагностика боксу |
| `dtsdiff.py` | диф DTS-дерев |
| `iomux_decode.py` | декодування iOMUX-регістрів |
| `pin_idle_scan.py` | скан пінів в idle |
| `pincfg_audit.py` | аудит pin-cfg |
| `make_bt_mode.py`, `make_bt_mode2.py` | генерація BT-режиму |
| `enable_uart0.py` | увімкнення UART0 |

**Реверс-інженерія ядра (витягнуті/анотовані копії):**
`gp.c`, `gp2.c`, `gpiolib.c`, `gpiolib-show.c`, `prk.c`, `mmc_core.c`, `pwrseq_simple.c`, `consumer.h`, `t.c` — читання драйверів ядра RK (GPIO/pinctrl/mmc) для розуміння mux-ланцюгів.

**DTS/діагностика:**
`mx9pro-board.dts`, `remote_installed-mx9pro-board.dts`, `remote_live-tree.dts`, `remote_v6-live.dts`, `remote_stock-rk3318-box.dts` — живі та стокові дерева; `remote_mx9diag.txt`, `remote_mx9dmesg.txt` — діагностика/dmesg; `grf-our-boot.txt` — GRF-регістри свого бута; `armbian-utils-Packages.txt` — перелік пакетів.

## Файли з кореня C:\ (префікс `root-`)

| Файл | Що це |
|---|---|
| `root-bt-switcher.sh`, `root-bt-switcher-v7.sh` | перемикач WiFi↔BT GPIO pin-mux для MX9 Pro (RK3328/RTL8723BS), v7 — фінальна |
| `root-bt_enable.dtbo` | DT-overlay увімкнення BT |
| `root-rk3328-mx9pro-v6.dtb`, `root-rk3328-mx9pro-v7.dtb` | скомпільовані DTB v6/v7 |

(«root-» префікс — щоб відрізняти від копій всередині іншої папки; дублікат `mx9pro-board.dts` був байт-в-байт і не дублювався.)

Пов'язане: дослідження проектору того ж автора — [projector-research](https://github.com/vladikit-bit/projector-research).
