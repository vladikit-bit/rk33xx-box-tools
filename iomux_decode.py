#!/usr/bin/env python3
"""Read the RK3328 GRF IOMUX registers and report the mux function of every
GPIO pad. This is ground truth from the hardware, independent of the pinctrl
core's bookkeeping (which is what confused the earlier sysfs-based scan).

GRF GPIO mux registers on RK3328 (grf + 0x000.. is SOC_CON*, IOMUX for the
banks lives at these offsets, 4 regs per bank covering A/B/C/D ports):
  GPIO0 IOMUX: 0x050,0x054,0x058,0x05c
  GPIO1 IOMUX: 0x060,0x064,0x068,0x06c
  GPIO2 IOMUX: 0x070,0x074,0x078,0x07c
  GPIO3 IOMUX: 0x080,0x084,0x088,0x08c
Each pad gets 2 bits; pad n of a port = bits (2*n, 2*n+1).
"""
import re
import sys

GRF = '/sys/kernel/debug/regmap/dummy-syscon@0x00000000ff100000/registers'
OFF = {0: 0x050, 1: 0x060, 2: 0x070, 3: 0x080}


def read_grf():
    vals = {}
    try:
        with open(GRF) as fh:
            for line in fh:
                m = re.match(r'^([0-9a-f]{3}):\s*([0-9a-f]{8})', line.strip())
                if m:
                    vals[int(m.group(1), 16)] = int(m.group(2), 16)
    except Exception as exc:
        print('cannot read GRF regmap:', exc)
        sys.exit(1)
    return vals


def mux_of(vals, bank, port, pad):
    """Return the 2-bit mux function for a pad."""
    base = OFF[bank] + port * 4
    reg = vals.get(base)
    if reg is None:
        return None
    return (reg >> (pad * 2)) & 0x3


PORTNAME = 'ABCD'

INTEREST = {
    # (bank, port, pad) -> why we care
    (3, 0, 0): 'SDIO_EXT CMD',
    (3, 0, 1): 'SDIO_EXT DETn',
    (3, 0, 2): 'SDIO_EXT CLK',
    (3, 0, 4): 'SDIO data0 <-> UART1 TX',
    (3, 0, 5): 'SDIO data1 <-> UART1 RTS',
    (3, 0, 6): 'SDIO data2 <-> UART1 RX',
    (3, 0, 7): 'SDIO data3 <-> UART1 CTS',
    (3, 1, 0): 'chip REG_ON (wifi_enable_h)',
    (2, 1, 5): 'bt-dis   (vendor pin group)',
    (2, 1, 3): 'chip-en  (vendor pin group)',
    (2, 1, 7): 'host-wake-bt',
    (2, 2, 0): 'bt-wake-host',
    (1, 1, 5): 'dusun BT-enable candidate',
    (1, 1, 6): 'dusun BT-host-wake candidate',
    (1, 1, 7): 'dusun BT-dev-wake candidate',
}


def main():
    vals = read_grf()
    print('=== RK3328 GRF IOMUX: mux function of pads of interest ===')
    print('(0 = GPIO function; nonzero = that pad is routed to a peripheral)\n')
    for (bank, port, pad), why in INTEREST.items():
        m = mux_of(vals, bank, port, pad)
        reg = OFF[bank] + port * 4
        raw = vals.get(reg, 0)
        flag = ''
        if m not in (None, 0):
            flag = '  <-- NOT a GPIO'
        print(f'GPIO{bank}_{PORTNAME[port]}{pad}  mux={m}  '
              f'(reg 0x{reg:03x}=0x{raw:08x})  {why}{flag}')

    print('\n=== any pad anywhere with mux != 0 (routed to a peripheral) ===')
    for bank in (0, 1, 2, 3):
        for port in range(4):
            reg = OFF[bank] + port * 4
            raw = vals.get(reg)
            if raw is None:
                continue
            active = []
            for pad in range(8):
                m = (raw >> (pad * 2)) & 0x3
                if m:
                    active.append(f'{PORTNAME[port]}{pad}=mux{m}')
            if active:
                print(f'GPIO{bank}_{PORTNAME[port]}: ' + ' '.join(active))


main()