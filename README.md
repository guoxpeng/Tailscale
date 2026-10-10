# Tailscale 安卓汉化版

基于官方 Tailscale Android 客户端的修改版，增加代理模式、内置浏览器和完整中文汉化。

> **当前版本：1.104.1**（真实版本号，Tailscale 控制台显示一致）
> 基于官方 `tailscale.com v1.104.1` Go 核心构建。

## 功能特性

### VPN 开启时
- 流量自动走 Tailscale 隧道（100.64.0.0/10）

### VPN 关闭时
- **代理模式**：将 Tailscale 作为本地 SOCKS5/HTTP 代理运行，无需 VPN 权限
  - SOCKS5: `127.0.0.1:1080`
  - HTTP: `127.0.0.1:8080`
  - 不与 Clash 等其他 VPN/代理应用冲突
- **内置浏览器**：无需配置代理，直接访问 Tailnet 上的 HTTP/FTP 服务
- 仍显示设备 IP 列表

### 分流模式
- 仅路由 Tailscale 流量，其他流量走系统默认路由
- 可与 Clash 等其他 VPN/代理应用同时使用
- 需重启 VPN 生效

### 完整中文汉化
- 500+ 界面字符串全中文
- 设置页代理/分流模式说明已汉化

## 已知问题

- 首次启动代理模式需等待 tsnet 连接（约 10-30 秒），期间状态显示连接中
- Android 14 上建议关闭预测性返回手势（已在 Manifest 中默认关闭，避免系统导航库闪退）

## 下载安装

从 [Releases](https://github.com/guoxpeng/tailscale-zh/releases/tag/v1.104.1) 下载最新 APK
（文件名形如 `Tailscale-zh-1.104.1.apk`）。

> ℹ️ **每个 Release 里同时挂着 Windows 与 Android 两个安装包** ——
> `Tailscale-zh-*-setup.exe`（Windows 一体化安装包）与 `Tailscale-zh-*.apk`（本端），
> 按扩展名取自己需要的那个即可。两条流水线写同一个 Release（标签 `v<版本号>`），
> 各自只覆盖自己那个文件。

> ⚠️ 安装前需卸载官方版 Tailscale（签名不同），安装后重新登录。

## 自动打包与发布

只需打一个标签，GitHub Actions 就会自动构建**全架构 APK** 并写进对应版本的 Release：

```bash
git tag android-v1.104.1          # 标签格式：android-v<版本号>
git push origin android-v1.104.1
```

- 发版标签是 **`v<版本号>`**（如 `v1.104.1`）—— 与 Windows 侧**共用同一个 Release**，
  所以打开该 Release 能同时看到 apk 与 exe；本流水线只覆盖 apk，不动 exe。
- 每次发布只追加**一个 apk**（全架构：arm64-v8a + armeabi-v7a + x86 + x86_64）。
- 也可以在仓库 Actions 页面手动触发：只构建并保存产物，不发布 Release。
- 签名用的是仓库内 [`.ci/android-debug.keystore`](.ci/) 这把**固定调试密钥**，
  因此各版本签名一致，用户可**直接覆盖安装升级**，不必反复卸载重装。

> ⚠️ 从早期手工构建的版本（如 `v3-fix`）升级仍需**先卸载一次**，之后就不会再有这个问题。

## 发布历史

- `v1.104.1`：统一发版标签 —— 同一个 Release 里同时挂着 Windows 安装包与 Android APK。
  （此前的 `android-v1.104.1`、`v3-fix`、`v1.104.1-zh` 等单端 Release 已合并/下线，标签保留。）

## 本地构建

需要 Go、Android SDK、Android NDK：

```bash
# 安装 Android SDK 组件
make androidsdk

# 构建 debug 版
make tailscale-debug
# 输出: ./tailscale-debug.apk

# 构建 release 版
make apk
```

详见 [官方构建文档](https://github.com/tailscale/tailscale/wiki)。

## 致谢

- [Tailscale](https://tailscale.com) 官方团队
- [pjjush16/tailscale-android-proxy](https://github.com/pjjush16/tailscale-android-proxy) 代理模式原作者

## License

BSD 3-Clause，与上游一致。见 [LICENSE](LICENSE)。
