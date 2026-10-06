#!/usr/bin/env python3
"""Build a BT-mode variant of the MX9Pro vendor DTS.

Two edits, applied to a DECOMPILED dts:

1. serial@ff120000 (UART1 = RTL8723BS Bluetooth) — give it its real pin
   groups so the BT UART actually reaches the module. The pads are
   GPIO3_A4 (TX), GPIO3_A6 (RX), GPIO3_A7 (CTS), GPIO3_A5 (RTS), mux 4.
   Phandles 0x22/0x23/0x24 are the vendor's uart1-xfer / -cts / -rts
   groups (verified present in this exact tree).

2. mmc@ff5f0000 (WiFi SDIO host) — set status = "disabled" so its probe
   never claims those same four pads, and so the scan loop that kept
   re-initialising the card is gone. The separate /sdio-pwrseq node is
   deliberately LEFT ENABLED: it keeps holding GPIO3_B0 (wifi_enable_h)
   high, which is what keeps the combo chip powered while only BT runs.
"""

import re
import sys

path = sys.argv[1]

with open(path, encoding='utf-8', errors='replace') as fh:
    lines = fh.read().split('\n')


def node_span(lines, node_label):
    """Return (start, end) line indices of the node starting at node_label."""
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(node_label + ' {'):
            start = i
            break
    if start is None:
        raise SystemExit('node not found: ' + node_label)

    depth = 0
    for j in range(start, len(lines)):
        depth += lines[j].count('{') - lines[j].count('}')
        if depth == 0:
            return start, j
    raise SystemExit('unbalanced braces at: ' + node_label)


def set_prop(lines, start, end, name, value, replace=True):
    """Insert or replace a property inside a node span.

    dtc requires every property to appear BEFORE the node's first child
    node, so a missing property is inserted right after the opening brace.
    """
    pat = re.compile(r'^\s*' + re.escape(name) + r'\s*=')
    for i in range(start, end + 1):
        if pat.match(lines[i]):
            if not replace:
                return False
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            lines[i] = f'{indent}{name} = {value};'
            return True

    # No such property: place it directly after the node's opening line.
    open_indent = lines[start][:len(lines[start]) - len(lines[start].lstrip())]
    lines.insert(start + 1, f'{open_indent}\t{name} = {value};')
    return True


# --- 1. UART1 gets its real Bluetooth pin groups -------------------------
s, e = node_span(lines, 'serial@ff120000')
set_prop(lines, s, e, 'pinctrl-names', '"default"')
set_prop(lines, s, e, 'pinctrl-0', '<0x22 0x23 0x24>')
set_prop(lines, s, e, 'status', '"okay"')
print('uart1: pinctrl-0 = <0x22 0x23 0x24>, status = okay')

# --- 2. WiFi SDIO host off, so it cannot fight UART1 for the pads -------
s, e = node_span(lines, 'mmc@ff5f0000')
set_prop(lines, s, e, 'status', '"disabled"')
print('mmc@ff5f0000: status = disabled (pwrseq node left enabled for power)')

with open(path, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines))
print('BT-mode DTS written')