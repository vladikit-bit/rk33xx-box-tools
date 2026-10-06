#!/usr/bin/env python3
"""Enable uart0 (serial@ff110000) in a decompiled DTS by flipping status to okay.

Used to TEST whether the MX9Pro's RTL8723BS Bluetooth UART is routed to
GPIO1_A8/A9 (uart0-xfer, completely unclaimed by anything on this board)
instead of the uart1 pads that physically collide with the WiFi SDIO bus.
"""
import re
import sys

path = sys.argv[1]
target = 'serial@ff110000'

with open(path, encoding='utf-8', errors='replace') as fh:
    lines = fh.read().split('\n')

out = []
in_node = False
depth = 0
changed = False

for line in lines:
    stripped = line.strip()

    if not in_node:
        # Node header line, e.g. "\tserial@ff110000 {"
        if stripped.startswith(target + ' {'):
            in_node = True
            depth = 1
            out.append(line)
            continue
    else:
        depth += line.count('{') - line.count('}')
        if re.match(r'^status\s*=\s*"disabled"', stripped):
            indent = line[:len(line) - len(line.lstrip())]
            out.append(f'{indent}status = "okay";')
            changed = True
            continue
        out.append(line)
        if depth <= 0:
            in_node = False
        continue

    out.append(line)

if not changed:
    print('ERROR: did not find status="disabled" inside ' + target)
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(out))

print('uart0 enabled OK')