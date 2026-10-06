#!/usr/bin/env python3
"""BT-mode DTB for MX9Pro: UART1 owns the pad group, WiFi SDIO host off.

Same base as make_bt_mode.py, but ALSO adds the RTL8723BS control pins as
real hogs so their level is deterministic at boot instead of floating on the
board's pull-ups:

  GPIO2_B5 (bank2 pin21) = bt-dis        -> driven LOW  (section enabled)
  GPIO2_B3 (bank2 pin19) = chip-en       -> driven HIGH (chip powered)
  GPIO2_B7 (bank2 pin15) = host-wake-bt  -> driven LOW  (let BT send wake)

Hogs are used (not devices) so nothing needs a driver, and they are easy to
remove later by reverting the DTB.

Note: global line numbers = bank*32 + pin, so these are global 85, 83, 79.
"""

import re
import sys

path = sys.argv[1]

with open(path, encoding='utf-8', errors='replace') as fh:
    lines = fh.read().split('\n')


def node_span(lines, node_label):
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
    raise SystemExit('unbalanced braces: ' + node_label)


def set_prop(lines, start, end, name, value):
    pat = re.compile(r'^\s*' + re.escape(name) + r'\s*=')
    for i in range(start, end + 1):
        if pat.match(lines[i]):
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            lines[i] = f'{indent}{name} = {value};'
            return
    indent = lines[start][:len(lines[start]) - len(lines[start].lstrip())]
    lines.insert(start + 1, f'{indent}\t{name} = {value};')


# 1. UART1 (BT UART) gets its real pad groups: A4 TX, A6 RX, A5 RTS, A7 CTS
s, e = node_span(lines, 'serial@ff120000')
set_prop(lines, s, e, 'pinctrl-names', '"default"')
set_prop(lines, s, e, 'pinctrl-0', '<0x22 0x23 0x24>')
set_prop(lines, s, e, 'status', '"okay"')
print('uart1: pinctrl-0 = <0x22 0x23 0x24>, status = okay')

# 2. WiFi SDIO host off (frees the pads it shares with UART1)
s, e = node_span(lines, 'mmc@ff5f0000')
set_prop(lines, s, e, 'status', '"disabled"')
print('mmc@ff5f0000: status = disabled (sdio-pwrseq left enabled for chip power)')

# 3. Deterministic RTL8723BS control lines on GPIO2.
s, e = node_span(lines, 'gpio@ff230000')
hog = (
    '\t\tmx9-hogs {\n'
    '\t\t\tbt-disable-lo {\n'
    '\t\t\t\tgpio-hog;\n'
    '\t\t\t\tgpios = <21 0>;\n'
    '\t\t\t\toutput-low;\n'
    '\t\t\t\tline-name = "bt-dis";\n'
    '\t\t\t};\n'
    '\t\t\tchip-enable-hi {\n'
    '\t\t\t\tgpio-hog;\n'
    '\t\t\t\tgpios = <19 0>;\n'
    '\t\t\t\toutput-high;\n'
    '\t\t\t\tline-name = "chip-en";\n'
    '\t\t\t};\n'
    '\t\t\thost-wake-bt-lo {\n'
    '\t\t\t\tgpio-hog;\n'
    '\t\t\t\tgpios = <15 0>;\n'
    '\t\t\t\toutput-low;\n'
    '\t\t\t\tline-name = "host-wake-bt";\n'
    '\t\t\t};\n'
    '\t\t};\n'
)
lines.insert(e, hog.rstrip('\n'))
print('gpio@ff230000: added 3 hogs (bt-dis=lo, chip-en=hi, host-wake-bt=lo)')

with open(path, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines))
print('BT-mode DTS v2 written')