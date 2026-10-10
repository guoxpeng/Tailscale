# -*- coding: utf-8 -*-
"""Tailscale Windows 界面汉化补丁器 v6
= v5（保长替换 + 扩容 + 重叠字面量否定检查）+ 一条对照表转义解析：

  v6 新增：对照表的英文/中文列支持 \\r \\n \\t \\\\ \\xHH 转义。
  原因：Unattended Mode / Exit node 两个确认框的正文本身就是**一条含
  \\r\\n\\r\\n 的多行长字符串**，TSV 是逐行解析的，没法直接写换行；
  行尾空格（如 "Connected - "）也容易被编辑器吞掉，故一并支持 \\x20。

  按 UTF-8 字节数比较长度，中文 ≤ 英文即可保长替换（补空格）；
  超出才走 .rsrc 尾部零填充扩容区，并把 LEAQ disp32 重定向过去。

用法: py313 patch_zh.py <in.exe> <out.exe> <zh_map.tsv> [report.txt]
"""
import struct
import sys
import io
import os
import re
import bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

# Windows 上控制台 / 管道的默认编码可能是 cp1252 或 cp936，
# 直接打印中文会抛 UnicodeEncodeError（英文 CI runner 上必现）。
# 统一强制 UTF-8 输出，保证任何环境都能把构建跑完。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

src, dst, mapfile = sys.argv[1], sys.argv[2], sys.argv[3]
report_path = sys.argv[4] if len(sys.argv) > 4 else None

data = bytearray(open(src, 'rb').read())
orig = bytes(data)

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


# ---------- 反汇编 ----------
_, tva, tvs, tra, trs = [s for s in sects if s[0] == '.text'][0]
base = ib + tva
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.skipdata = True
RE_RIP = re.compile(r'\[rip ([+-]) (0x[0-9a-f]+)\]')
RE_IMM = re.compile(r'^(0x[0-9a-f]+|\d+)$')

insns = list(md.disasm_lite(data[tra:tra + trs], base))
leas = {}      # tgt_va -> [(ioff, size)]
decl = {}      # tgt_va -> set(声明长度)
decl_imm = {}  # (tgt_va, ioff) -> 该条 LEAQ 之后「首个写寄存器的 MOV reg,imm」的 imm32 偏移
movs = []      # (imm_off, imm) 供兜底式宽松匹配
for idx, (addr, size, mn, ops) in enumerate(insns):
    ioff = tra + (addr - base)
    if mn == 'lea':
        m = RE_RIP.search(ops)
        if m:
            d = int(m.group(2), 16)
            if m.group(1) == '-':
                d = -d
            tgt = addr + size + d
            leas.setdefault(tgt, []).append((ioff, size))
            # 紧随其后 3 条指令内首个【写入寄存器】的 MOV reg, imm —— Go 里即字符串长度
            # 注意：写内存的 mov（mov qword ptr [rax+0x30], 6）是结构体字段赋值，不是长度
            for j in range(idx + 1, min(idx + 4, len(insns))):
                a2, s2, m2, o2 = insns[j]
                if m2 in ('mov', 'movabs'):
                    dstr = o2.split(', ', 1)[0]
                    if '[' in dstr or 'ptr' in dstr:
                        continue
                    last = o2.rsplit(', ', 1)[-1]
                    if RE_IMM.match(last):
                        v = int(last, 16) if last.startswith('0x') else int(last)
                        if 1 <= v <= 300:
                            decl.setdefault(tgt, set()).add(v)
                            # imm32 在指令末尾
                            decl_imm[(tgt, ioff)] = tra + (a2 - base) + s2 - 4
                        break
                if m2 in ('ret', 'jmp', 'call'):
                    break
    elif mn == 'mov':
        last = ops.rsplit(', ', 1)[-1]
        if RE_IMM.match(last) and size >= 5:
            v = int(last, 16) if last.startswith('0x') else int(last)
            if v <= 0xFFFFFFFF:
                movs.append((ioff + size - 4, v))
movs.sort()
mov_offs = [m[0] for m in movs]


def len_imms(ioff, L, before=96, after=96):
    lo = bisect.bisect_left(mov_offs, ioff - before)
    hi = bisect.bisect_right(mov_offs, ioff + after)
    return [o for k in range(lo, hi) for o, v in [movs[k]] if v == L]


def ptr_heads(v, L):
    res = []
    needle = struct.pack('<Q', v)
    j = orig.find(needle)
    while j >= 0:
        if off2sec(j) in ('.data', '.rdata') and struct.unpack_from('<Q', orig, j + 8)[0] == L:
            res.append(j)
        j = orig.find(needle, j + 1)
    return res


# ---------- 扩容区 ----------
rsrc = [s for s in sects if s[0] == '.rsrc'][0]
slack_off = rsrc[3] + rsrc[2]
slack_va = ib + rsrc[1] + rsrc[2]
slack_size = rsrc[4] - rsrc[2]
assert orig[slack_off:slack_off + slack_size] == b'\0' * slack_size, '扩容区不是全零'
grow_cursor = 0


def alloc(buf):
    global grow_cursor
    need = len(buf)
    if grow_cursor + need > slack_size:
        raise MemoryError('扩容区不足')
    o = slack_off + grow_cursor
    data[o:o + need] = buf
    va = slack_va + grow_cursor
    grow_cursor += need
    return va


def unesc(s):
    """还原对照表里的转义写法。

    多行对话框文案（如 Unattended Mode 确认框）本身带 \\r\\n，无法直接写进
    以换行分行的 TSV；行尾空格也容易被编辑器吞掉，所以统一用转义表示：
        \\r  \\n  \\t  \\\\  \\xHH（HH 为两位十六进制，用于行尾空格等）
    不认识的转义按原样保留，保证老表里的普通反斜杠不被误改。
    """
    out = []
    i = 0
    simple = {'r': '\r', 'n': '\n', 't': '\t', '\\': '\\'}
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n in simple:
                out.append(simple[n])
                i += 2
                continue
            if n == 'x' and i + 3 < len(s) + 1 and len(s) >= i + 4:
                try:
                    out.append(chr(int(s[i + 2:i + 4], 16)))
                    i += 4
                    continue
                except ValueError:
                    pass
        out.append(c)
        i += 1
    return ''.join(out)


entries = []
for line in io.open(mapfile, encoding='utf-8-sig'):
    line = line.rstrip('\r\n')
    if not line.strip() or line.lstrip().startswith('#'):
        continue
    p = line.split('\t')
    if len(p) == 2:
        entries.append((unesc(p[0]), unesc(p[1])))

log = io.open(report_path, 'w', encoding='utf-8', newline='\n') if report_path else None


def say(s):
    print(s)
    if log:
        log.write(s + '\n')


say('源: %s (%d 字节)   扩容区 VA=0x%x 大小=%d' % (os.path.basename(src), len(orig), slack_va, slack_size))
say('')

n_ok = n_grow = 0
skipped = []
conflicts = []

for en, zh in entries:
    b, z = en.encode(), zh.encode()
    L, Z = len(b), len(z)
    offs = []
    j = orig.find(b)
    while j >= 0:
        if off2sec(j) == '.rdata':
            offs.append(j)
        j = orig.find(b, j + 1)

    matched = []
    n_rej = 0
    for o in offs:
        v = off2va(o)
        # —— v5 新增：声明长度不一致 -> 判定为更长字面量内部，拒绝 ——
        bad = [d for d in decl.get(v, set()) if d != L]
        if bad:
            n_rej += 1
            conflicts.append('  REJECT %-30s @0x%x(VA=0x%x) 声明长度=%s != %d'
                             % (en, o, v, sorted(decl.get(v, set())), L))
            continue
        refs = []
        for (ioff, size) in leas.get(v, []):
            # 优先取「该条 LEAQ 之后首个写寄存器 MOV」的精确 imm 偏移（v6）；
            # 取不到再退回 ±96 字节等值匹配（老逻辑，可能误伤同值的结构体字段）
            imm = decl_imm.get((v, ioff))
            if imm is not None and struct.unpack_from('<I', data, imm)[0] == L:
                li = [imm]
            else:
                li = len_imms(ioff, L)
            if li:
                refs.append(('LEA', ioff, size, li))
        for h in ptr_heads(v, L):
            refs.append(('HDR', h, 0, [h + 8]))
        if refs:
            matched.append((o, refs))

    note = ''
    # 回退（数据段指针引用）仅在没有任何位置被判「重叠」时才启用，避免绕过保护
    if not matched and len(offs) == 1 and n_rej == 0:
        matched = [(offs[0], [])]
        note = '  [无静态引用,唯一副本→保长替换]'
    if not matched:
        skipped.append((en, zh, 'no-ref(%d副本)' % len(offs)))
        continue

    if Z <= L:
        pad = b' ' * (L - Z)
        for (o, refs) in matched:
            data[o:o + L] = z + pad
        n_ok += 1
        say('OK    %-32s -> %-18s %d->%d 字节  副本=%d%s' % (en, zh, L, Z, len(matched), note))
        continue

    va_new = alloc(z)
    patched = 0
    for (o, refs) in matched:
        for (kind, ioff, size, extra) in refs:
            if kind == 'LEA':
                next_ip = ib + tva + (ioff - tra) + size
                struct.pack_into('<i', data, ioff + size - 4, va_new - next_ip)
                for imm_off in extra:
                    cur = struct.unpack_from('<I', data, imm_off)[0]
                    if cur != L:
                        # 宁可直接失败，也不写出长度不一致的损坏 exe
                        raise SystemExit(
                            '长度立即数校验失败 @0x%x: 期望 %d 实际 %d' % (imm_off, L, cur))
                    struct.pack_into('<I', data, imm_off, Z)
                patched += 1
            else:
                struct.pack_into('<Q', data, ioff, va_new)
                struct.pack_into('<Q', data, ioff + 8, Z)
                patched += 1
    if patched == 0:
        skipped.append((en, zh, 'grow-no-ref'))
        continue
    n_grow += 1
    say('GROW  %-32s -> %-18s %d->%d 字节  新VA=0x%x  改动=%d' % (en, zh, L, Z, va_new, patched))

say('')
say('保长替换: %d 条    扩容: %d 条    未处理: %d 条' % (n_ok, n_grow, len(skipped)))
for en, zh, why in skipped:
    say('   SKIP [%s] %s -> %s' % (why, en, zh))
if conflicts:
    say('')
    say('因「声明长度不符」被拒（重叠字面量保护）:')
    for c in conflicts:
        say(c)

open(dst, 'wb').write(bytes(data))
changed = sum(1 for a, c in zip(orig, data) if a != c)
say('')
say('输出: %s (%d 字节)  改变字节数=%d  扩容区已用 %d/%d' % (dst, len(data), changed, grow_cursor, slack_size))
if log:
    log.close()
