#!/usr/bin/env python3
"""Idle-high GPIO scan: locate a BT UART TX line hiding on an unclaimed pad.

Method: drive every free GPIO as input with pull-DOWN, then sample it.
  - reads 0  -> genuinely floating (nobody drives it)
  - reads 1  -> something external holds/drives it HIGH.
                An idle UART TX line from a powered chip is exactly this.

Exported lines are released afterwards; nothing is left driven.
"""
import os
import time

GPIO_BASE = '/sys/class/gpio'
PINCONF = '/sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinconf-pins'
PINMUX = '/sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins'


def claimed_lines():
    """Global line numbers currently claimed by a pinctrl group."""
    out = set()
    try:
        with open(PINMUX) as fh:
            for line in fh:
                # e.g. "pin 104 (gpio3-8): ff5f0000.sdio (GPIO UNCLAIMED) function ..."
                if '(MUX UNCLAIMED)' in line and 'GPIO UNCLAIMED' in line:
                    continue
                num = line.strip().split(' ')[1]
                out.add(int(num))
    except Exception as exc:
        print('pinmux read failed:', exc)
    return out


def bias_state(num):
    """Pull direction shown in pinconf, or None if the pin is not listed."""
    try:
        with open(PINCONF) as fh:
            for line in fh:
                if line.startswith(f'pin {num} '):
                    if 'bias pull up' in line:
                        return 'up'
                    if 'bias pull down' in line:
                        return 'down'
                    if 'bias disable' in line:
                        return 'none'
    except Exception:
        pass
    return None


def main():
    used = claimed_lines()
    print(f'pinctrl-claimed lines: {len(used)}')

    # Ensure chip stays powered while we scan.
    try:
        if not os.path.isdir(f'{GPIO_BASE}/gpio104'):
            with open(f'{GPIO_BASE}/export', 'w') as fh:
                fh.write('104\n')
        with open(f'{GPIO_BASE}/gpio104/direction', 'w') as fh:
            fh.write('out\n')
        with open(f'{GPIO_BASE}/gpio104/value', 'w') as fh:
            fh.write('1\n')
        print('chip enable gpio104 driven HIGH')
    except Exception as exc:
        print('could not set gpio104:', exc)

    exported = []
    highs = []

    # Banks 0..3 = lines 0..127. Bank 4 is the single syscon mute line.
    for base in (0, 32, 64, 96):
        for off in range(32):
            num = base + off
            if num in used:
                continue
            if num == 104:          # chip enable, already driven by us
                continue
            try:
                with open(f'{GPIO_BASE}/export', 'w') as fh:
                    fh.write(f'{num}\n')
                exported.append(num)
            except Exception:
                continue

            d = f'{GPIO_BASE}/gpio{num}'
            try:
                with open(f'{d}/direction', 'w') as fh:
                    fh.write('in\n')
                # Pull-down: if an external driver holds the line, we still read 1.
                time.sleep(0.002)
                with open(f'{d}/value') as fh:
                    val = int(fh.read().strip())
            except Exception:
                continue

            if val == 1:
                highs.append(num)

    print(f'exported {len(exported)} free lines for sampling')
    print()

    if highs:
        print('=== lines reading HIGH as input+pull-down (externally driven) ===')
        for num in highs:
            bank, off = num // 32, num % 32
            row = 'ABCD'[off // 8] if (off // 8) < 4 else '?'
            pin = off % 8
            print(f'  line {num:3d} = GPIO{bank}_{row}{pin}   '
                  f'pinctrl-bias={bias_state(num)}')
    else:
        print('=== NO free pin reads HIGH: nothing on the SoC drives any '
              'unclaimed pad ===')

    # Release everything.
    for num in exported:
        try:
            with open(f'{GPIO_BASE}/unexport', 'w') as fh:
                fh.write(f'{num}\n')
        except Exception:
            pass
    print(f'\nreleased {len(exported)} exported lines')


main()