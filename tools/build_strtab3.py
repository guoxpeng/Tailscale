# -*- coding: utf-8 -*-
"""精确字符串常量表：对每个 LEAQ 目标，用其后紧邻的长度立即数定长。
用法: py313 build_strtab3.py <exe> <out.tsv>
输出: VA \t len \t 文本
"""
import struct
import sys
import io
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

# Windows 上默认输出编码可能是 cp1252，打印中文会 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

exe, outfile = sys.argv[1], sys.argv[2]
data = open(exe, 'rb').read()

pe = struct.unpack_from('<I', data, 0x3c)[0]
opt = pe + 24
nsec, = struct.unpack_from('<H', data, pe + 6)
optsize, = struct.unpack_from('<H', data, pe + 20)
ib, = struct.unpack_from('<Q', data, opt + 24)
sects = []
for i in range(nsec):
    so = opt + optsize + i * 40
    nm = data[so:so + 8].rstrip(b'\0').decode('latin1')
    vs, va, rs, ra = struct.unpack_from('<IIII', data, so + 8)
    sects.append((nm, va, vs, ra, rs))


def off2sec(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs:
            return nm
    return '?'


def va2off(v):
    r = v - ib
    for nm, va, vs, ra, rs in sects:
        if va <= r < va + vs:
            return ra + (r - va)
    return None


_, tva, tvs, tra, trs = [s for s in sects if s[0] == '.text'][0]
base = ib + tva
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.skipdata = True
RE_RIP = re.compile(r'\[rip ([+-]) (0x[0-9a-f]+)\]')
RE_IMM = re.compile(r'^(0x[0-9a-f]+|\d+)$')

leas = {}
movs = []
for addr, size, mn, ops in md.disasm_lite(data[tra:tra + trs], base):
    ioff = tra + (addr - base)
    if mn == 'lea':
        m = RE_RIP.search(ops)
        if m:
            d = int(m.group(2), 16)
            if m.group(1) == '-':
                d = -d
            leas.setdefault(addr + size + d, []).append(ioff)
    elif mn in ('mov', 'movabs'):
        last = ops.rsplit(', ', 1)[-1]
        if RE_IMM.match(last):
            movs.append((ioff, int(last, 16) if last.startswith('0x') else int(last)))
movs.sort()

out = io.open(outfile, 'w', encoding='utf-8', newline='\n')
out.write('# VA\tlen\tLEAQ数\t文本\n')
rows = 0
for tgt in sorted(leas):
    o = va2off(tgt)
    if o is None or off2sec(o) != '.rdata':
        continue
    maxlen = 0
    while maxlen < 300 and 32 <= data[o + maxlen] < 127:
        maxlen += 1
    if maxlen < 2:
        continue
    ioffs = sorted(leas[tgt])
    # 在任一 LEAQ 之后 0..72 字节内找第一个落在 [2,maxlen] 的立即数，作为长度
    L = None
    for ioff in ioffs:
        for (mo, mv) in movs:
            if ioff + 2 <= mo <= ioff + 72:
                if 2 <= mv <= maxlen:
                    if L is None or mv > L:
                        L = mv
                    break
        if L:
            break
    if not L:
        continue
    txt = data[o:o + L].decode('latin1')
    out.write('0x%x\t%d\t%d\t%s\n' % (tgt, L, len(ioffs), txt))
    rows += 1
out.close()
print('精确常量条目: %d -> %s' % (rows, outfile))
