#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tailscale Windows 汉化构建脚本

用法:
    python tools/build.py <原版 tailscale-ipn.exe> <输出目录>

流程:
    1. 校验输入 exe 的大小与 SHA256 —— 补丁是按**文件偏移**改的，源文件必须是
       完全相同的官方构建，否则会改错位置把程序打崩。不匹配直接报错退出。
    2. 调用 tools/patch_zh.py 生成汉化版。
    3. 校验产物 SHA256 与基准一致（防止汉化表/补丁逻辑被无声改坏）。

产物:
    <输出目录>/tailscale-ipn.zh.exe   汉化后的 tailscale-ipn.exe
    <输出目录>/patch-report.txt       逐条补丁明细

环境变量:
    ALLOW_TS_HASH_MISMATCH=1      放行「输入与预期不符」，仅用于调试新版本
    ALLOW_TS_OUT_HASH_MISMATCH=1  放行「产物与基准不符」，改了汉化表之后用
"""
import hashlib
import os
import subprocess
import sys

# Windows 上控制台 / 管道的默认编码可能是 cp1252 或 cp936，
# 直接打印中文会抛 UnicodeEncodeError（英文 CI runner 上必现）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---- 目标版本常量（换 Tailscale 版本时必须同步更新） ----
TS_VERSION = "1.104.1"

# 官方 tailscale-setup-1.104.1-amd64.msi 中 ClientGUIx64（= tailscale-ipn.exe）
ORIG_SHA256 = "0c3c56a6626c9f71a32fb307dbda0c810c94a89d66fed158258da6f043004f9c"
ORIG_SIZE = 29622776

# 用 tools/zh_win.tsv 打补丁后的确定性产物
# （v5 对照表：118 条生效 = 保长 102 + 扩容 16；改动汉化表后此值必须同步更新）
OUT_SHA256 = "cc527deb8573bd404e3b23da0279cfa4efac85babbffaaaeb6e1d3094406b4d5"

HERE = os.path.dirname(os.path.abspath(__file__))
PATCHER = os.path.join(HERE, "patch_zh.py")
TABLE = os.path.join(HERE, "zh_win.tsv")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg):
    print("ERROR: " + msg, file=sys.stderr)
    return 1


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2

    src, outdir = argv[1], argv[2]
    if not os.path.isfile(src):
        return fail("找不到输入文件: %s" % src)
    os.makedirs(outdir, exist_ok=True)

    size = os.path.getsize(src)
    digest = sha256(src)
    if size != ORIG_SIZE or digest != ORIG_SHA256:
        msg = (
            "输入 exe 与预期不符（补丁按文件偏移改写，源文件必须完全一致）\n"
            "  期望: Tailscale %s, %d 字节, SHA256=%s\n"
            "  实际: %d 字节, SHA256=%s"
            % (TS_VERSION, ORIG_SIZE, ORIG_SHA256, size, digest)
        )
        if os.environ.get("ALLOW_TS_HASH_MISMATCH") != "1":
            print("ERROR: " + msg, file=sys.stderr)
            print(
                "官方若已换版，需要重新做一份 zh_win.tsv 偏移表并更新本文件常量。",
                file=sys.stderr,
            )
            return 3
        print("WARNING: " + msg)

    out = os.path.join(outdir, "tailscale-ipn.zh.exe")
    report = os.path.join(outdir, "patch-report.txt")

    rc = subprocess.call([sys.executable, PATCHER, src, out, TABLE, report])
    if rc != 0:
        return fail("patch_zh.py 退出码 %d" % rc)

    out_digest = sha256(out)
    if out_digest != OUT_SHA256:
        msg = (
            "产物 SHA256 与基准不同\n"
            "  基准: %s\n"
            "  实际: %s" % (OUT_SHA256, out_digest)
        )
        if os.environ.get("ALLOW_TS_OUT_HASH_MISMATCH") != "1":
            print("ERROR: " + msg, file=sys.stderr)
            print(
                "若你是有意修改 tools/zh_win.tsv，请把上面的『实际』值更新到 "
                "tools/build.py 的 OUT_SHA256；否则说明补丁逻辑出了偏差。",
                file=sys.stderr,
            )
            return 4
        print("WARNING: " + msg)

    print("OK: 产物 %s (%d 字节) SHA256=%s" % (out, os.path.getsize(out), out_digest))
    print("    报告 %s" % report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
