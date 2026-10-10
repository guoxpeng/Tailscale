@echo off
chcp 65001 >nul
setlocal
title Tailscale 界面汉化 - 安装 / 还原

rem ============================================================
rem  一键安装 / 还原 Tailscale Windows 界面汉化
rem
rem  安装: 右键本文件 -> 以管理员身份运行（需与本脚本同目录有
rem        tailscale-ipn.zh.exe）
rem  还原: install_zh.bat restore
rem ============================================================

set "SRC=%~dp0tailscale-ipn.zh.exe"
set "DEST_DIR=%ProgramFiles%\Tailscale"
set "DST=%DEST_DIR%\tailscale-ipn.exe"
set "BAK=%DEST_DIR%\tailscale-ipn.exe.orig"
set "OLDBAK=%DEST_DIR%\tailscale-ipn.exe.orig.bak"

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [!] 需要管理员权限：请右键本文件 -^> "以管理员身份运行"
  pause & exit /b 1
)
if not exist "%DST%" (
  echo [!] 未找到已安装的 Tailscale: %DST%
  pause & exit /b 1
)

if /i "%~1"=="restore" goto RESTORE

if not exist "%SRC%" (
  echo [!] 未找到汉化文件: %SRC%
  echo     请把 tailscale-ipn.zh.exe 与本脚本放在同一目录。
  pause & exit /b 1
)

echo [1/4] 备份官方原版 -^> tailscale-ipn.exe.orig
if not exist "%BAK%" copy /Y "%DST%" "%BAK%" >nul

echo [2/4] 关闭 Tailscale 托盘程序
taskkill /IM tailscale-ipn.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo [3/4] 写入汉化版
copy /Y "%SRC%" "%DST%" >nul

echo [4/4] 重新启动 Tailscale
start "" "%DST%"

echo.
echo  完成！点击托盘里的 Tailscale 图标即可看到中文界面。
echo  还原官方英文版:  install_zh.bat restore
echo.
pause
exit /b 0

:RESTORE
set "RESTORE_SRC=%BAK%"
if not exist "%RESTORE_SRC%" set "RESTORE_SRC=%OLDBAK%"
if not exist "%RESTORE_SRC%" (
  echo [!] 未找到备份（既没有 tailscale-ipn.exe.orig 也没有 tailscale-ipn.exe.orig.bak）
  pause & exit /b 1
)
echo 正在还原官方原版 ...
taskkill /IM tailscale-ipn.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul
copy /Y "%RESTORE_SRC%" "%DST%" >nul
start "" "%DST%"
echo 已还原。
pause
exit /b 0
