# Tailscale 安卓汉化版

基于官方 Tailscale Android 客户端的修改版，增加代理模式、内置浏览器和完整中文汉化。

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

## 下载安装

从 [Releases](../../releases) 下载最新 APK。

> ⚠️ 安装前需卸载官方版 Tailscale（签名不同），安装后重新登录。

## 自动打包

推送到 `main` 分支或打 tag 时，GitHub Actions 自动构建 APK 并上传到 Releases。

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
