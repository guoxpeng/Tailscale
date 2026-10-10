# Tailscale Windows 汉化

> ⚠️ **这是补丁包，不是完整安装程序！**
> **必须先装好官方原版 Tailscale 1.104.1**，再运行本汉化包。
> **不要先卸载官方版**——安装程序需要备份原版 `tailscale-ipn.exe`，没有原版文件会直接报错中止。


把 Tailscale **Windows 桌面端**（`tailscale-ipn.exe`，托盘图标与主面板）的界面文字替换成简体中文。

- 基版本：**Tailscale 1.104.1 (x64)**
- 方式：对官方二进制做**偏移补丁**（保长原地替换为主），不重新编译
- 产出：**向导式安装包**（Inno Setup），也可单独取汉化后的 `tailscale-ipn.exe`

> 只替换托盘 / 主界面程序 `tailscale-ipn.exe`，**不改动** `tailscaled` 服务、WinTun 驱动以及其它任何文件。

---

## 一、直接使用

### 方式 A：安装包（推荐）

1. 先装好官方 [Tailscale 1.104.1](https://pkgs.tailscale.com/stable/tailscale-setup-1.104.1-amd64.msi)（x64）。
2. 下载本仓库 Release 里的 `Tailscale-zh-1.104.1-setup.exe`，**右键 → 以管理员身份运行**。
3. 安装程序会：退出托盘程序 → 把官方原版备份为 `tailscale-ipn.exe.orig` → 写入汉化版 → 重新拉起托盘程序。
4. 卸载「Tailscale 中文汉化」即可**自动还原**官方版本。
   托盘程序会随卸载一起退出，从开始菜单重新打开 Tailscale 即可；
   `tailscaled` 服务与其网络连通性全程不受影响。

### 方式 B：手动替换

```
1. 右键托盘图标 → 退出 Tailscale
2. 备份  C:\Program Files\Tailscale\tailscale-ipn.exe
3. 用 tailscale-ipn.zh.exe 覆盖它（需管理员权限）
4. 重新运行 C:\Program Files\Tailscale\tailscale-ipn.exe
```

仓库里的 [`prebuilt/tailscale-ipn.zh.exe`](prebuilt/) 是已经**实机验证可用**的成品，
可直接下载使用；其 SHA256 见同目录 `SHA256SUMS.txt`，与 CI 构建产物逐字节一致。

### 方式 C：一键脚本

下载 Release 里的 `install_zh.bat`，与 `tailscale-ipn.zh.exe` 放在**同一目录**，
**右键 → 以管理员身份运行**即可；`install_zh.bat restore` 还原官方原版。

脚本会先把官方原版备份为 `tailscale-ipn.exe.orig`（若你之前用过旧版脚本，
它会兼容读取旧的 `.orig.bak`），再写入汉化版并重启托盘程序。

---

## 二、汉化范围

共 **47 条**界面文案，覆盖主面板、Preferences（设置）、账号子菜单、Exit nodes（出口节点）子菜单等。
完整中英对照见 [`tools/zh_win.tsv`](tools/zh_win.tsv)。

| 类别 | 例子 |
| --- | --- |
| 连接状态 | `Connected` → 已连接 · `Disconnected. Click to connect.` → 未连接，点击连接 |
| 菜单项 | `Preferences` → 设置 · `Log &out` → 注销 · `&Add another account...` → &添加其他账号... |
| 设备列表 | `This device: %s (%s)` → 本机: %s (%s) · `unknown device` → 未知设备 |
| 出口节点 | `Exit nodes` → 出口 · `Run exit node...` → 运行出口节点 · `Best Available` → 最佳可用 |

---

## 三、实现原理（简述）

Go 编译的二进制把字符串常量**连续**堆在 `.rdata` 里，代码用 `LEAQ` 取地址 + `MOV` 加载长度来引用。
补丁器的做法：

1. 用 [capstone](https://www.capstone-engine.org/) **全量反汇编** `.text`，建立 `地址 → [(引用指令, 声明长度)]` 表。
2. **保长替换为主**：中文 UTF-8 字节数 ≤ 英文时，原地写入中文 + 空格补齐。
   长度一字节不变 ⇒ 不用改任何指令，对 `LEAQ`、静态 `{ptr,len}` 头、数据段指针等**任何引用方式都自动生效**。本版 47 条里有 44 条走这条路。
3. **扩容**：中文更长时（`Exit`、`Run exit node...`、`Run exit node?` 共 3 条），写入 `.rsrc` 尾部
   504 字节全零空档，并同步改写引用处的 `LEAQ` 位移与长度立即数。
4. **重叠字面量保护**（关键）：`.rdata` 里存在共享前缀的字面量，例如 `Preferences`(11) 与
   `PreferencesMenu`(15) 相邻存放。后者是 syspolicy 设置键，用来拼 Prometheus 指标名；
   若被误改成中文会直接 `panic: illegal metric name`。
   因此对每个候选地址，取其 `LEAQ` 之后**紧随的首个「写寄存器」`MOV reg, imm`** 作为*声明长度*，
   只要与当前串长度不符就**拒绝该位置**。

## 四、构建

### 本地构建

```bash
python -m pip install capstone

# 1) 取官方原始程序（MSI 内文件名为 ClientGUIx64）
curl.exe -L -o tailscale-setup.msi https://pkgs.tailscale.com/stable/tailscale-setup-1.104.1-amd64.msi
"C:\Program Files\7-Zip\7z.exe" x tailscale-setup.msi -oextract -y

# 2) 打补丁（内含 SHA256 校验，源文件不符会直接报错）
python tools/build.py extract/ClientGUIx64 build

# 3) 校验产物
python tools/verify.py extract/ClientGUIx64 build/tailscale-ipn.zh.exe tools/zh_win.tsv
```

产物在 `build/`：`tailscale-ipn.zh.exe` + `patch-report.txt`。

### 编译安装包

```bash
# 需先装 Inno Setup 6（CI 里固定用 6.7.3）
ISCC.exe installer\tailscale-zh.iss
# 产物: dist\Tailscale-zh-1.104.1-setup.exe
```

不想在系统里装 Inno Setup 也可以免安装解压一份来用（Inno 自己的安装包支持 `/PORTABLE=1`）：

```bash
innosetup-6.7.3.exe /PORTABLE=1 /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=inno
inno\ISCC.exe installer\tailscale-zh.iss
```

> 改完 `.iss` 建议先在本地跑一次上面的编译再推 CI：
> 编译器能直接指出脚本函数用错（例如 `FileSize` 是 `var` 出参而非返回值、
> `ExecAsOriginalUser` 在卸载阶段不可调用），比等 CI 快得多。

### CI 自动构建

`.github/workflows/build-pc-installer.yml`：推送到 `pc` 分支（或手动触发 `workflow_dispatch`）时，
自动下载官方 MSI → 校验 SHA256 → 打补丁 → 校验产物 → 装 Inno Setup 6.7.3 → 编译安装包 → 上传 Artifact。
打 `pc-v*` 标签时额外发布 Release。

CI 会在**源文件哈希不符**时直接失败（不会产出错误的包），因此 Tailscale 换版后不会静默出错。

---

## 五、目录

```
.
├── .github/workflows/build-pc-installer.yml   CI：自动出安装包
├── installer/
│   ├── tailscale-zh.iss                       Inno Setup 安装包脚本
│   └── ChineseSimplified.isl                  安装向导简中语言包（取自 issrc 同版本 tag）
├── scripts/install_zh.bat                     一键安装 / 还原脚本
├── prebuilt/tailscale-ipn.zh.exe              已实机验证的成品（含 SHA256SUMS.txt）
├── tools/
│   ├── build.py                               构建入口（含源/产物 SHA256 校验）
│   ├── patch_zh.py                            汉化补丁器（核心）
│   ├── verify.py                              产物校验器
│   ├── analyze_refs.py                        RIP 相对引用扫描（排查用）
│   ├── build_strtab3.py                       字符串常量表提取（排查用）
│   └── zh_win.tsv                             47 条中英对照表
└── docs/patch-report.txt                      最近一次补丁明细
```

---

## 六、注意事项

- **数字签名失效**：改动后的 `tailscale-ipn.exe` 不再有 Tailscale 官方签名，Windows 可能提示「未知发布者」。
- **自动更新会覆盖汉化**：请到「设置 → 自动安装&更新」取消勾选（`Automatically install &updates`）。
- **换版本要重做偏移表**：补丁依赖精确的文件偏移，Tailscale 升级后 `zh_win.tsv` 与 `build.py` 里的
  SHA256 常量都需要更新；CI 会在源文件哈希不符时直接失败，不会产出错误的包。
- 本项目仅为界面汉化，与 Tailscale Inc. 无关联，不分发其源码或未修改的官方二进制。
