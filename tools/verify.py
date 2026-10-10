#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汉化产物校验器

用法:
    python tools/verify.py <原版.exe> <汉化.exe> [tools/zh_win.tsv]

校验项:
    1. 文件长度一致（本方案以「保长替换」为主，长度不应改变）。
    2. 每条汉化是否真的落位（中文写入 + 空格补齐）。
    3. .rdata 内所有差异区间都能对应到某个替换目标，没有越界误伤。
    4. 重叠字面量（如 PreferencesMenu）逐字节未变 —— 改了会让 Go 程序
       触发 panic: illegal metric name，必须为 0 差异。
    5. 扩容条目的引用已被改写到 .rsrc 空档区。

退出码: 0 = 全部通过；1 = 存在失败项。
"""
import io
import os
import re
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

# 绝不允许被改动的重叠字面量（改了会 panic: illegal metric name）
MUST_KEEP = [b"PreferencesMenu"]

# 扩容条目（中文更长，写入 .rsrc 空档）：英文 -> 预期中文前缀
GROWN_HINT = ["运行出口节点", "退出"]


class PE(object):
    def __init__(self, data):
        self.d = data
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        opt = pe + 24
        nsec = struct.unpack_from("<H", data, pe + 6)[0]
        optsize = struct.unpack_from("<H", data, pe + 20)[0]
        self.ib = struct.unpack_from("<Q", data, opt + 24)[0]
        self.sects = []
        for i in range(nsec):
            so = opt + optsize + i * 40
            nm = data[so:so + 8].rstrip(b"\0").decode("latin1")
            vs, va, rs, ra = struct.unpack_from("<IIII", data, so + 8)
            self.sects.append((nm, va, vs, ra, rs))

    def sec(self, name):
        for s in self.sects:
            if s[0] == name:
                return s
        return None

    def off2sec(self, o):
        for nm, va, vs, ra, rs in self.sects:
            if ra <= o < ra + rs:
                return nm
        return "?"

    def va2off(self, v):
        r = v - self.ib
        for nm, va, vs, ra, rs in self.sects:
            if va <= r < va + rs:
                return ra + (r - va)
        return None


def diffs(a, b):
    out, i, n = [], 0, min(len(a), len(b))
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def load_table(path):
    rows = []
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        p = line.split("\t")
        if len(p) == 2:
            rows.append((p[0], p[1]))
    return rows


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2

    orig = open(argv[1], "rb").read()
    zh = open(argv[2], "rb").read()
    table = argv[3] if len(argv) > 3 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "zh_win.tsv")

    fails = []
    po, pz = PE(orig), PE(zh)

    print("原版 %d 字节   汉化 %d 字节" % (len(orig), len(zh)))
    if len(orig) != len(zh):
        fails.append("文件长度改变（%d -> %d）" % (len(orig), len(zh)))
        print("  [FAIL] 文件长度改变")
    else:
        print("  [ OK ] 文件长度一致")

    # ---- 1. 重叠字面量必须原样 ----
    print("\n-- 重叠字面量保护 --")
    for lit in MUST_KEEP:
        o = orig.find(lit)
        if o < 0:
            print("  [skip] 原版找不到 %r" % lit)
            continue
        same = orig[o:o + len(lit)] == zh[o:o + len(lit)]
        print("  [%s] %r @0x%x" % (" OK " if same else "FAIL", lit.decode(), o))
        if not same:
            fails.append("重叠字面量被改动: %r @0x%x" % (lit.decode(), o))

    # ---- 2. 每条汉化是否落位 ----
    entries = load_table(table)
    print("\n-- 替换落位检查（共 %d 条）--" % len(entries))
    covered = []
    n_ok = n_grow = 0
    for en, z in entries:
        b, zb = en.encode(), z.encode()
        if len(zb) > len(b):
            n_grow += 1
            continue
        pad = b" " * (len(b) - len(zb))
        hit = 0
        j = orig.find(b)
        while j >= 0:
            if zh[j:j + len(zb)] == zb and zh[j + len(zb):j + len(b)] == pad:
                hit += 1
                covered.append((j, j + len(b)))
            j = orig.find(b, j + 1)
        if hit:
            n_ok += 1
        else:
            print("  [FAIL] 未找到替换结果: %r -> %r" % (en, z))
            fails.append("未落位: %r" % en)
    print("  保长替换落位 %d 条 / 扩容条目 %d 条" % (n_ok, n_grow))

    # ---- 3. 差异字节必须全部被替换区间覆盖 ----
    # 注意：相邻的两次替换之间没有未改动字节，diff 会把它们连成一段，
    # 因此这里按「字节是否落在某个替换区间内」判断，而不是按整段包含。
    print("\n-- 差异字节覆盖检查（.rdata）--")
    cover = bytearray(len(orig))
    for (a, b) in covered:
        for k in range(a, min(b, len(cover))):
            cover[k] = 1
    uncovered = []
    for (a, b) in diffs(orig, zh):
        if po.off2sec(a) != ".rdata":
            continue
        if not all(cover[k] for k in range(a, b)):
            uncovered.append((a, b))
    if uncovered:
        print("  [FAIL] %d 个差异区间含未被替换覆盖的字节:" % len(uncovered))
        for a, b in uncovered[:20]:
            print("     0x%x+%d %r" % (a, b - a, orig[a:b]))
        fails.append("有未预期的差异字节（%d 处）" % len(uncovered))
    else:
        print("  [ OK ] 所有差异字节都能对应到替换目标")

    # ---- 4. 扩容引用 + 收集「可合法改写的 4 字节窗口」 ----
    print("\n-- 扩容条目引用检查 --")
    tva, tra, trs = pz.sec(".text")[1], pz.sec(".text")[3], pz.sec(".text")[4]
    text_base = pz.ib + tva
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.skipdata = True
    RE_RIP = re.compile(r"\[rip ([+-]) (0x[0-9a-f]+)\]")
    RE_IMMS = re.compile(r"^(0x[0-9a-f]+|\d+)$")

    spans = []   # (start, end, 说明)：允许被改写的 4 字节窗口
    refs = []
    for ins in md.disasm(zh[tra:tra + trs], text_base):
        ioff = tra + (ins.address - text_base)
        if ins.mnemonic == "lea" and RE_RIP.search(ins.op_str):
            # LEAQ 的 disp32 位于指令末尾 4 字节
            spans.append((ioff + ins.size - 4, ioff + ins.size, "LEA disp32"))
            m = RE_RIP.search(ins.op_str)
            d = int(m.group(2), 16)
            if m.group(1) == "-":
                d = -d
            o = pz.va2off(ins.address + ins.size + d)
            if o is None or pz.off2sec(o) != ".rsrc":
                continue
            s = zh[o:o + 64]
            end = s.find(b"\0")
            raw = s[:end if end >= 0 else 64]
            try:
                txt = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if any(txt.startswith(h) for h in GROWN_HINT):
                refs.append((hex(ins.address), txt))
        elif ins.mnemonic in ("mov", "movabs") and ins.size >= 5:
            dst = ins.op_str.split(",", 1)[0]
            last = ins.op_str.rsplit(",", 1)[-1].strip()
            if "[" not in dst and "ptr" not in dst and RE_IMMS.match(last):
                spans.append((ioff + ins.size - 4, ioff + ins.size, "MOV imm32"))

    if refs:
        for a, t in refs:
            print("  [ OK ] 扩容串 %r 由 LEAQ @%s 引用" % (t, a))
    else:
        print("  [warn] 未定位到扩容引用（可能改用其它编码形式）")

    # ---- 5. .text 改动必须只落在上面那些 4 字节窗口内 ----
    print("\n-- .text 改动位置检查 --")
    tsec = po.sec(".text")
    tdiff = [(a, b) for (a, b) in diffs(orig, zh) if po.off2sec(a) == ".text"]
    if not tdiff:
        print("  [ OK ] .text 无改动（本次全部为保长替换）")
    else:
        bad = []
        for (a, b) in tdiff:
            hit = [d for (s, e, d) in spans if s <= a and b <= e]
            va = po.ib + tsec[1] + (a - tsec[3])
            if hit:
                print("  [ OK ] 0x%08x +%-2d %-11s %r -> %r"
                      % (va, b - a, hit[0], orig[a:b], zh[a:b]))
            else:
                print("  [FAIL] 0x%08x +%-2d 非法位置   %r -> %r"
                      % (va, b - a, orig[a:b], zh[a:b]))
                bad.append((a, b))
        if bad:
            fails.append(".text 有 %d 处改动不在 LEAQ 位移 / MOV 长度立即数上" % len(bad))

    print()
    if fails:
        print("==== 校验未通过：%d 项 ====" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    print("==== 校验全部通过 ====")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
