@echo off
chcp 936 >nul 2>&1
setlocal
title Tailscale 界面汉化 - 安装 / 还原

rem ============================================================
rem  一键安装 / 还原 Tailscale Windows 界面汉化
rem
rem  安装: 右键本文件 -> 以管理员身份运行（需与本脚本同目录有
rem        tailscale-ipn.zh.exe）
rem  还原: install_zh.bat restore
rem
rem  行为与安装包（installer/tailscale-zh.iss）保持一致：
rem    - 原版只备份一次为 tailscale-ipn.exe.orig，重复安装不会把它覆盖掉
rem    - 写入失败会重试 5 次，仍失败则明确报错（不再误报「完成」）
rem    - 用 explorer 转交启动托盘，避免以管理员身份运行 Tailscale GUI
rem ============================================================

rem 取 64 位 Program Files：%ProgramFiles% 在 32 位宿主进程里会被重定向到 (x86)
set "PF=%ProgramW6432%"
if not defined PF set "PF=%ProgramFiles%"

set "SRC=%~dp0tailscale-ipn.zh.exe"
set "DEST_DIR=%PF%\Tailscale"
set "DST=%DEST_DIR%\tailscale-ipn.exe"
set "BAK=%DEST_DIR%\tailscale-ipn.exe.orig"
set "OLDBAK=%DEST_DIR%\tailscale-ipn.exe.orig.bak"

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [!] 需要管理员权限：请右键本文件 -^> "以管理员身份运行"
  pause & exit /b 1
)

if /i "%~1"=="restore" goto RESTORE

if not exist "%DST%" (
  echo [!] 未找到已安装的 Tailscale: %DST%
  pause & exit /b 1
)
if not exist "%SRC%" (
  echo [!] 未找到汉化文件: %SRC%
  echo     请把 tailscale-ipn.zh.exe 与本脚本放在同一目录。
  pause & exit /b 1
)

echo [1/4] 备份官方原版 -^> tailscale-ipn.exe.orig
if not exist "%BAK%" (
  copy /Y "%DST%" "%BAK%" >nul
  if errorlevel 1 (
    echo [!] 备份原版失败，已中止（未改动任何文件）
    pause & exit /b 1
  )
)

echo [2/4] 关闭 Tailscale 托盘程序
taskkill /IM tailscale-ipn.exe /F >nul 2>&1
ping -n 3 127.0.0.1 >nul

echo [3/4] 写入汉化版
set "OK="
for /L %%i in (1,1,5) do (
  copy /Y "%SRC%" "%DST%" >nul 2>&1
  if not errorlevel 1 (
    set "OK=1"
    goto :INSTALLED
  )
  echo     第 %%i 次写入失败（文件可能仍被占用），重试 ...
  ping -n 3 127.0.0.1 >nul
)
:INSTALLED
if not defined OK (
  echo [!] 写入汉化版失败：请先手动退出 Tailscale 托盘程序，再以管理员身份重跑本脚本。
  pause & exit /b 1
)

echo [4/4] 重新启动 Tailscale
rem 用 explorer 转交启动：本脚本是提权运行的，直接 start 会让 Tailscale GUI
rem 以管理员身份运行（官方不支持这种用法）；交给已在用户会话中的 explorer
rem 处理，可让它以当前登录用户身份启动。
explorer.exe "%DST%"

echo.
echo  完成！点击托盘里的 Tailscale 图标即可看到中文界面。
echo  还原官方英文版:  install_zh.bat restore
echo.
pause
exit /b 0

:RESTORE
rem 还原分支不要求主程序当前存在 —— 目标就是把它放回去
set "RESTORE_SRC=%BAK%"
if not exist "%RESTORE_SRC%" set "RESTORE_SRC=%OLDBAK%"
if not exist "%RESTORE_SRC%" (
  echo [!] 未找到备份（既没有 tailscale-ipn.exe.orig 也没有 tailscale-ipn.exe.orig.bak）
  pause & exit /b 1
)

echo 正在还原官方原版 ...
taskkill /IM tailscale-ipn.exe /F >nul 2>&1
ping -n 3 127.0.0.1 >nul

set "OK="
for /L %%i in (1,1,5) do (
  copy /Y "%RESTORE_SRC%" "%DST%" >nul 2>&1
  if not errorlevel 1 (
    set "OK=1"
    goto :RESTORED
  )
  echo     第 %%i 次还原失败（文件可能仍被占用），重试 ...
  ping -n 3 127.0.0.1 >nul
)
:RESTORED
if not defined OK (
  echo [!] 还原失败：请先手动退出 Tailscale 托盘程序，再以管理员身份重跑。
  pause & exit /b 1
)

explorer.exe "%DST%"
echo 已还原。
pause
exit /b 0
