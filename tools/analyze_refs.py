# -*- coding: utf-8 -*-
"""全模式引用点扫描：对每个目标字面量，找出所有可能的代码/数据引用。
用法: py313 analyze_refs.py <exe> <zh_map.tsv> <out.txt>

覆盖模式：
  A) .text 中所有 RIP 相对 LEAQ（支持任意 REX 前缀 0x40-0x4F，以及无 REX 的 8D 05）
  B) 打印每个 .rdata occurrence 的左右边界（判断是否为更长字符串的子串）
  C) 全文件 8 字节绝对指针 == 字面量 VA（静态 {ptr,len} 头）
  D) LEAQ 附近 ±256 字节内匹配原长度的立即数（多编码形式）
"""
import struct
import sys
import io

# Windows 上默认输出编码可能是 cp1252，打印中文会 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

exe, mapfile, outfile = sys.argv[1], sys.argv[2], sys.argv[3]
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


def off2va(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs:
            return ib + va + (o - ra)
    return None


_, tva, tvs, tra, trs = [s for s in sects if s[0] == '.text'][0]


def code_va(off):
    return ib + tva + (off - tra)


# ---------- A) 全量 RIP 相对 LEAQ ----------
leas = {}
i = data.find(b'\x8d', tra, tra + trs - 8)
cnt = 0
while i >= 0:
    modrm = data[i + 1]
    if (modrm & 0xC7) == 0x05:
        rex = 1 if (i - 1 >= tra and 0x40 <= data[i - 1] <= 0x4F) else 0
        ioff = i - rex
        ilen = 6 + rex
        disp, = struct.unpack_from('<i', data, i + 2)
        tgt = code_va(ioff) + ilen + disp
        leas.setdefault(tgt, []).append(ioff)
        cnt += 1
        i = data.find(b'\x8d', i + ilen, tra + trs - 8)
        continue
    i = data.find(b'\x8d', i + 1, tra + trs - 8)


# ---------- D) 长度立即数候选（在窗口内按编码模式匹配） ----------
def len_imm_at(k, length):
    """判断文件偏移 k 起的 4 字节是否是某个 mov 指令的长度立即数。"""
    if k < 4 or k + 4 > len(data):
        return None
    val, = struct.unpack_from('<I', data, k)
    if val != length:
        return None
    b1 = data[k - 1]
    # mov r32, imm32   (B8+rd)
    if 0xB8 <= b1 <= 0xBF:
        return 'mov-r32'
    # mov r8d, imm32   (41 B8+rd)
    if k >= 2 and data[k - 2] == 0x41 and 0xB8 <= b1 <= 0xBF:
        return 'mov-r8d'
    # mov r/m32, imm32 (C7 /0)
    if k >= 2 and data[k - 2] == 0xC7 and (b1 & 0xF8) == 0x00:
        return 'mov-rm32'
    # mov r/m64, imm32 (48 C7 /0)
    if k >= 3 and data[k - 3] == 0x48 and data[k - 2] == 0xC7 and (b1 & 0xF8) == 0x00:
        return 'mov-rm64'
    # mov r/m64, imm32 (49 C7 /0)
    if k >= 3 and data[k - 3] == 0x49 and data[k - 2] == 0xC7 and (b1 & 0xF8) == 0x00:
        return 'mov-rm64-wb'
    # mov r64, imm64 (48 B8+rd) —— 8 字节立即数，低 4 字节先看
    if k >= 2 and data[k - 2] == 0x48 and 0xB8 <= b1 <= 0xBF:
        return 'movabs-lo'
    return None


def find_len_imms(code_off, length, before=256, after=200):
    lo = max(4, code_off - before)
    hi = min(len(data) - 4, code_off + 7 + after)
    hits = []
    # 只扫描窗口内的 B8/C7/41/48/49 字节作为锚点，避免逐字节
    for anchor in (0xB8, 0xC7, 0x41, 0x48, 0x49):
        j = data.find(bytes([anchor]), lo, hi)
        while j >= 0:
            for trial in (j + 1, j + 2, j + 3, j + 4):
                m = len_imm_at(trial, length)
                if m:
                    hits.append((trial, m))
            j = data.find(bytes([anchor]), j + 1, hi)
    # 也覆盖 b8..bf 全部
    for b in range(0xB9, 0xC0):
        j = data.find(bytes([b]), lo, hi)
        while j >= 0:
            m = len_imm_at(j + 1, length)
            if m:
                hits.append((j + 1, m))
            j = data.find(bytes([b]), j + 1, hi)
    return sorted(set(hits))


def find_ptrs(v):
    res = []
    needle = struct.pack('<Q', v)
    j = data.find(needle)
    while j >= 0:
        sec = off2sec(j)
        if sec in ('.data', '.rdata'):
            ln, = struct.unpack_from('<Q', data, j + 8)
            res.append((j, ln, sec))
        j = data.find(needle, j + 1)
    return res


def printable(c):
    return 32 <= c < 127 or c >= 0x80


entries = []
for line in io.open(mapfile, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line.strip() or line.lstrip().startswith('#'):
        continue
    p = line.split('\t')
    if len(p) == 2:
        entries.append((p[0], p[1]))

out = io.open(outfile, 'w', encoding='utf-8', newline='\n')
out.write('LEAQ 总数(去重目标): %d   指令数: %d\n' % (len(leas), cnt))

for en, zh in entries:
    b = en.encode()
    L = len(b)
    z = zh.encode()
    out.write('\n' + '=' * 78 + '\n')
    out.write('### %s   (EN %d 字节 / ZH %d 字节)  ->  %s\n' % (en, L, len(z), zh))
    offs = []
    j = data.find(b)
    while j >= 0:
        if off2sec(j) == '.rdata':
            offs.append(j)
        j = data.find(b, j + 1)
    if not offs:
        out.write('  [.rdata 中未找到]\n')
        continue
    for o in offs:
        v = off2va(o)
        pre = data[o - 1] if o > 0 else 0
        post = data[o + L] if o + L < len(data) else 0
        sub = (printable(pre) and pre not in (0,)) or (printable(post) and post not in (0,))
        out.write('  occ 0x%x  VA=0x%x  左=%s 右=%s  子串风险=%s\n' %
                  (o, v, chr(pre) if 32 <= pre < 127 else '0x%02x' % pre,
                   chr(post) if 32 <= post < 127 else '0x%02x' % post,
                   'YES' if sub else 'no'))
        # C) 静态头
        for (p, ln, sec) in find_ptrs(v):
            tag = 'HDR-OK ' if ln == L else 'HDR-diff(%d)' % ln
            out.write('      %s file=0x%x VA=0x%x sec=%s\n' % (tag, p, off2va(p), sec))
        # A+D) LEAQ + 长度立即数
        for ioff in leas.get(v, []):
            imm = find_len_imms(ioff, L)
            guard = 'OK' if imm else 'no-len-imm'
            out.write('      LEAQ file=0x%x VA=0x%x  %s  len_hits=%d\n' %
                      (ioff, code_va(ioff), guard, len(imm)))
            for (k, m) in imm[:6]:
                rel = k - ioff
                out.write('           len@0x%x (%+d)  %s\n' % (k, rel, m))
out.close()
print('written', outfile)
