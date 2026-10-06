import re, sys

def parse(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    # strip comments
    txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
    txt = re.sub(r'//[^\n]*', '', txt)
    root = {}
    stack = [(-1, root)]
    lines = txt.split('\n')
    i = 0
    cur_path = []
    while i < len(lines):
        raw = lines[i].strip()
        i += 1
        if not raw or raw.startswith('#'): continue
        if raw == '}':
            if len(stack) > 1: stack.pop()
            continue
        m = re.match(r'^([A-Za-z0-9,_@.+\-]+)\s*\{', raw)
        if m:
            name = m.group(1)
            parent = stack[-1][0]
            path = (stack[-1][1] + '/' + name) if stack[-1][1] else ('/' + name)
            node = {}
            if path in root: node = root[path]
            else: root[path] = node
            stack.append((1, node, path) if len(stack)==1 and False else (1, node))
            stack[-1] = (1, node)
            stack[-1] = (1, node)
            # store path in node for later
            node['__path__'] = path
            stack[-2] if False else None
            # we need stack of (node,path)
            continue
        m = re.match(r'^([A-Za-z0-9,_-]+)\s*=\s*(.*);$', raw)
        if m and len(stack) > 1:
            node = stack[-1][1]
            node[m.group(1)] = m.group(2).strip()
            continue
        m = re.match(r'^([A-Za-z0-9,_-]+)\s*=\s*(.*)$', raw)
        if m and len(stack) > 1:
            # continuation line
            node = stack[-1][1]
            prev = node.get(m.group(1), '')
            node[m.group(1)] = prev + ' ' + m.group(2).strip()
    return root

def flat(root):
    out = {}
    for path, node in root.items():
        for k, v in node.items():
            if k == '__path__': continue
            out[path + '::' + k] = v
    return out

a = flat(parse(sys.argv[1]))  # live
b = flat(parse(sys.argv[2]))  # v6

only_live = sorted(k for k in a if k not in b)
only_v6   = sorted(k for k in b if k not in a)
diff_val  = sorted(k for k in a if k in b and a[k] != b[k])

INTEREST = re.compile(r'gpio|mmc|sdio|pwrseq|cru|clock|regulator|i2c|sdmmc|vcc|wifi|io-domain|serial|uart|snps|reset', re.I)

print("### PROPERTY-LEVEL DIFFERENCES (same path, different value) ###")
n = 0
for k in diff_val:
    if INTEREST.search(k):
        n += 1
        print(f"  {k}\n      live: {a[k][:150]}\n      v6  : {b[k][:150]}")
print(f"  (total shown: {n} of {len(diff_val)})")

print("\n### NODES ONLY IN V6 (missing from live) ###")
for k in only_v6:
    if k.endswith('::') : continue
    node = k.split('::')[0]
    if INTEREST.search(node): print("  ", k, "=", b[k][:110])

print("\n### PROPERTIES ONLY IN LIVE (extra vs v6) ###")
for k in only_live:
    node = k.split('::')[0]
    if INTEREST.search(node): print("  ", k, "=", a[k][:110])
