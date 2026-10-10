# Tailscale Windows 汉化

> ✅ **现已一体化：安装包自带官方 Tailscale 1.104.1 组件，无需预装。**

**下载**：打开 [**Releases**](https://github.com/guoxpeng/tailscale-zh/releases) 取最新标签
（当前 `pc-v1.104.1-fix`）下的 `Tailscale-zh-1.104.1-setup.exe`。
CI 每次推送都会重新构建，Release 资产与源码逐字节对应。

> - **没装过 Tailscale 的电脑**：直接装本包即可 —— 会先**静默**装好官方组件
>   （`msiexec /qn`，全程无界面、无英文向导、无弹窗），再把界面换成中文版。
> - **已装 Tailscale 1.104.1 的电脑**：自动跳过官方安装，直接替换界面程序。
> - **装的是其它版本**：安装时会提示版本不匹配，由你决定是否继续。


把 Tailscale **Windows 桌面端**（`tailscale-ipn.exe`，托盘图标与主面板）的界面文字替换成简体中文。

- 基版本：**Tailscale 1.104.1 (x64)**
- 方式：对官方二进制做**偏移补丁**（保长原地替换为主），不重新编译
- 产出：**向导式安装包**（Inno Setup，约 38 MB，内嵌官方 MSI），也可单独取汉化后的 `tailscale-ipn.exe`

> 界面汉化只替换托盘 / 主界面程序 `tailscale-ipn.exe`，**不改动** `tailscaled` 服务与 WinTun 驱动。
> 未装 Tailscale 时，安装包会先用官方原始 MSI 静默装好完整组件，再打汉化。

---

## 一、直接使用

### 方式 A：安装包（推荐）

下载本仓库 Release 里的 `Tailscale-zh-1.104.1-setup.exe`，**右键 → 以管理员身份运行**。

安装程序会：

1. 检查目标机是否已装 Tailscale。
   - **没装** → 用随包的官方 MSI **静默**安装完整组件，再替换界面程序。
     **全新机器一步到位，不必先手动跑官方安装向导。**
   - **已装** → 跳过官方安装，只替换界面程序，并把原版备份为 `tailscale-ipn.exe.orig`。
2. 退出正在运行的托盘程序 → 写入汉化版 → 重新拉起托盘程序。

卸载「Tailscale 中文汉化」即可**自动还原**官方界面程序：

- 托盘程序会随卸载一起退出，从开始菜单重新打开 Tailscale 即可；
  `tailscaled` 服务、WinTun 驱动与网络连通性全程不受影响。
- 官方 Tailscale 本体**不会**被卸载（可在「应用和功能」里单独卸）。

### 方式 B：手动替换

> 前提：目标机已装**官方 Tailscale 1.104.1**。

```
1. 右键托盘图标 → 退出 Tailscale
2. 备份  C:\Program Files\Tailscale\tailscale-ipn.exe
3. 用 tailscale-ipn.zh.exe 覆盖它（需管理员权限）
4. 重新运行 C:\Program Files\Tailscale\tailscale-ipn.exe
```

仓库里的 [`prebuilt/tailscale-ipn.zh.exe`](prebuilt/) 是成品副本，可直接下载使用；
其 SHA256 见同目录 `SHA256SUMS.txt`，与 CI 从同一源码构建出的产物逐字节一致
（因此如果你要的是「确定能跑」的那份，Release 里的 `tailscale-ipn.zh.exe` 与它完全相同）。

### 方式 C：一键脚本

下载 Release 里的 `install_zh.bat`，与 `tailscale-ipn.zh.exe` 放在**同一目录**，
**右键 → 以管理员身份运行**即可；`install_zh.bat restore` 还原官方原版。

脚本会先把官方原版备份为 `tailscale-ipn.exe.orig`（若你之前用过旧版脚本，
它会兼容读取旧的 `.orig.bak`），再写入汉化版并重启托盘程序。

---

## 二、汉化范围

共 **118 条**界面文案，覆盖主面板、Preferences（设置）、账号子菜单、Exit nodes（出口节点）子菜单，
以及托盘提示、气泡通知、Taildrop 文件传输、更新提示、管理员批准/签署，
和**无人值守 / 出口节点确认对话框**等二级界面。
完整中英对照见 [`tools/zh_win.tsv`](tools/zh_win.tsv)。

| 类别 | 例子 |
| --- | --- |
| 连接状态 | `Connected` → 已连接 · `Connected - ` → 已连接 -  · `Connecting...` → 连接中... · `Connection lost` → 连接已断开 |
| 菜单项 | `Preferences` → 设置 · `Log &out` → 注销 · `Bug report...` → 问题反馈... · `Open with...` → 打开方式... |
| 设备列表 | `This device: %s (%s)` → 本机: %s (%s) · `unknown device` → 未知设备 · `Managed by %s` → 管理方 %s |
| 出口节点 | `Exit nodes` → 出口 · `Run exit node...` → 运行出口节点 · `No exit node available` → 无可用出口节点 |
| 托盘提示 | `Tailscale: Please log in.` → Tailscale: 请登录。 · `You are logged out. The last login error was: %v` → 您已注销。上次登录错误：%v |
| 文件传输 | `Ready to send %d files` → 准备发送 %d 个文件 · `You canceled the file transfer.` → 您取消了文件传输。 |
| 通知与状态 | `Tailscale Update Available` → Tailscale 有可用更新 · `Always On mode` → 常开模式 · `Latest %s version: %s` → 最新 %s 版本：%s |
| 网络异常 | `Tailscale could not connect to the '%s' relay server...` → Tailscale 无法连接中继服务器 '%s'。 · `You have enabled a non-default log target...` → 您已启用非默认的日志目标。 |
| 确认对话框 | `Are you sure you want to enable Unattended Mode?` → 确定要启用无人值守模式？ · `Are you sure you want to run an exit node?` → 确定要运行出口节点？ |
| 管理员操作 | `Admin Approval Needed` → 需要管理员批准 · `Your network admin needs to sign this computer...` → 网络管理员需要签署此计算机加入网络。 |

---

## 三、实现原理（简述）

Go 编译的二进制把字符串常量**连续**堆在 `.rdata` 里，代码用 `LEAQ` 取地址 + `MOV` 加载长度来引用。
补丁器的做法：

1. 用 [capstone](https://www.capstone-engine.org/) **全量反汇编** `.text`，建立 `地址 → [(引用指令, 声明长度)]` 表。
2. **保长替换为主**：中文 UTF-8 字节数 ≤ 英文时，原地写入中文 + 空格补齐。
   长度一字节不变 ⇒ 不用改任何指令，对 `LEAQ`、静态 `{ptr,len}` 头、数据段指针等**任何引用方式都自动生效**。本版 118 条里有 102 条走这条路。
3. **扩容**：中文更长时（本版 16 条），写入 `.rsrc` 尾部
   504 字节全零空档，并同步改写引用处的 `LEAQ` 位移与长度立即数。当前共用掉 323 字节。
4. **重叠字面量保护**（关键）：`.rdata` 里存在共享前缀的字面量，例如 `Preferences`(11) 与
   `PreferencesMenu`(15) 相邻存放。后者是 syspolicy 设置键，用来拼 Prometheus 指标名；
   若被误改成中文会直接 `panic: illegal metric name`。
   因此对每个候选地址，取其 `LEAQ` 之后**紧随的首个「写寄存器」`MOV reg, imm`** 作为*声明长度*，
   只要与当前串长度不符就**拒绝该位置**。
5. **多行文案**：无人值守 / 出口节点确认框的正文本身就是**一条含 `\r\n\r\n` 的长字符串常量**
   （例如 `Are you sure you want to enable Unattended Mode?` 那条 286 字节）。TSV 是逐行解析的，
   写不进真实换行，故对照表支持 `\r` `\n` `\t` `\\` `\xHH` 转义（行尾空格写作 `\x20`），
   由 `patch_zh.py` 在读取时还原；`verify.py` 用同一套还原逻辑，避免两边不一致。

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

安装包是否内嵌官方 MSI（即是否具备「一体化安装」能力），由编译期探测仓库根目录有没有
`tailscale-setup.msi` 决定（`#ifexist`）：

- **有** → 内嵌，约 38 MB，全新机器可直接一键装好；
- **没有** → 自动降级成「仅替换」模式，约 8.5 MB，要求目标机已装官方版。

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
│   └── zh_win.tsv                             118 条中英对照表（支持 \r\n\xHH 转义）
└── docs/patch-report.txt                      最近一次补丁明细
```

---

## 六、注意事项

- **数字签名失效**：改动后的 `tailscale-ipn.exe` 不再有 Tailscale 官方签名，Windows 可能提示「未知发布者」。
- **自动更新会覆盖汉化**：请到「设置 → 自动安装&更新」取消勾选（`Automatically install &updates`）。
- **换版本要重做偏移表**：补丁依赖精确的文件偏移，Tailscale 升级后 `zh_win.tsv` 与 `build.py` 里的
  SHA256 常量都需要更新；CI 会在源文件哈希不符时直接失败，不会产出错误的包。
- 本项目仅为界面汉化，与 Tailscale Inc. 无关联，不分发其源码或未修改的官方二进制。

---

## 七、更新日志

### `pc-v1.104.1-fix`（当前）

**修复**

- **安装包一体化**：`setup.exe` 内嵌官方 1.104.1 MSI。全新机器直接装本包即可，
  安装器先用 `msiexec /qn /norestart TS_NOLAUNCH=1` **静默**装好完整组件
  （无英文向导、无弹窗、不由官方安装器抢先拉起托盘），再替换界面程序。
- **补齐无人值守弹窗**：`Run unattended`（无人值守）确认框正文此前一直是英文。
  根因是**对话框正文本身就是一条 286 字节的多行长字符串常量**，从未被收录进对照表；
  标题 `Confirm unattended mode` 早已汉化，所以只看到正文是英文。现已汉化，
  出口节点确认框正文（249 字节）同理一并修复。
- **修掉 3 条「写了但没生效」的条目**：`You are logged out. The last login error was: %v`、
  `Connected - `、`Managed by %s`。旧表只收录了短前缀，被「重叠字面量保护」判定为
  更长字面量的子串而**拒绝落位**，界面因此一直是英文。
- 对照表新增 `\r` `\n` `\t` `\\` `\xHH` 转义（多行文案与行尾空格必需），
  `patch_zh.py` 与 `verify.py` 用同一套还原逻辑。
- 安装器新增**版本一致性检查**：检测到已装 `tailscale-ipn.exe` 大小与本包基准不符时
  弹窗确认，避免把不同版本的界面程序与 `tailscaled` 服务混用。

**汉化条目**：47 → **118 条**（保长替换 102 + 扩容 16，扩容区 323/504 字节）。

**刻意不收录**：`A request to sign the following device...` 看着像界面文案，实际是一条
更长的 Go 模板字面量（后方还接着 `{{.OSName}}<a href=...>`）。按句号截断替换会破坏模板渲染，
补丁器按「无长度立即数」自动 SKIP。

### `pc-v1.104.1`

- 首个 PC 版汉化（47 条界面文案），Inno Setup 向导式安装包，卸载自动还原。

### `v1.104.1-zh` / `v3-fix`

- Android 版汉化相关的历史标签，与 PC 安装包无关。
