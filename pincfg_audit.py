import re, sys, collections

def parse_dts(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    txt = re.sub(r'/\*.*?\*/', ' ', txt, flags=re.S)
    txt = re.sub(r'//[^\n]*', '', txt)
    lines = txt.split('\n')
    stack = []  # list of (node_name, props_dict)
    out = {}    # path -> props
    i = 0
    cur_path = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        # node open
        m = re.match(r'^([A-Za-z0-9,_@.+\-]+)\s*\{$', line)
        if m:
            name = m.group(1)
            p = (cur_path[-1] + '/' + name) if cur_path else '/' + name
            out[p] = {}
            cur_path.append(p)
            continue
        if line == '};' or line == '}':
            if cur_path:
                cur_path.pop()
            continue
        m = re.match(r'^([A-Za-z0-9,_-]+)\s*=\s*(.+?);$', line)
        if m and cur_path:
            out[cur_path[-1]][m.group(1)] = m.group(2).strip()
            continue
    return out

def find_gpio3b0_groups(tree):
    # rockchip,pins = <bank pin mux cfg ...>  bank=3 pin=8  => cells "0x03 0x08" or "3 8"
    groups = []
    for path, props in tree.items():
        pins = props.get('rockchip,pins', '')
        cells = re.findall(r'0x[0-9a-fA-F]+|\b\d+\b', pins)
        for k in range(0, len(cells) - 3, 4):
            try:
                bank = int(cells[k], 0); pin = int(cells[k+1], 0); mux = int(cells[k+2], 0); cfg = int(cells[k+3], 0)
            except ValueError:
                continue
            if bank == 3 and pin == 8:
                groups.append((path, mux, cfg))
                break
    return groups

tree = parse_dts(sys.argv[1])
groups = find_gpio3b0_groups(tree)
print(f"=== groups containing GPIO3_B0 ({len(groups)}) ===")
phandle_to_path = {}
for path, props in tree.items():
    ph = props.get('phandle')
    if ph:
        try: phandle_to_path[int(ph, 0)] = path
        except ValueError: pass

for gpath, mux, cfg in groups:
    cfg_path = phandle_to_path.get(cfg, '???')
    print(f"  group: {gpath}\n    mux={mux} pcfg={hex(cfg)} -> {cfg_path} props={tree.get(cfg_path, {})}")

print()
print("=== who references those groups (device <- pinctrl-0) ===")
group_phandles = {}
for path, props in tree.items():
    ph = props.get('phandle')
    if ph:
        try: group_phandles[int(ph, 0)] = path
        except ValueError: pass

for gpath, mux, cfg in groups:
    gph = tree.get(gpath, {}).get('phandle')
    if not gph:
        continue
    try: gphv = int(gph, 0)
    except ValueError: continue
    for path, props in tree.items():
        p0 = props.get('pinctrl-0', '')
        cells = re.findall(r'0x[0-9a-fA-F]+', p0)
        refs = [int(c, 16) for c in cells]
        if gphv in refs:
            status = props.get('status', '(default-ok)')
            compat = props.get('compatible', '(no compat)')
            print(f"  group {gpath.split('/')[-1]} (mux={mux}) referenced by: {path}")
            print(f"      compatible={compat} status={status}")
