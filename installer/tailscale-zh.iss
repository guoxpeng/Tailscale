; =====================================================================
;  Tailscale 中文汉化 —— Inno Setup 安装包脚本
;
;  只替换托盘 / 主界面程序 tailscale-ipn.exe，
;  **不触碰** tailscaled 服务、WinTun 驱动与其它任何文件。
;
;  安装: 把官方原版备份为 tailscale-ipn.exe.orig，再写入汉化版
;  卸载: 自动把 .orig 还原回 tailscale-ipn.exe
;
;  编译: ISCC.exe installer\tailscale-zh.iss
;  前置: ..\build\tailscale-ipn.zh.exe  （由 tools/build.py 生成）
; =====================================================================

#define MyZhName    "Tailscale 中文汉化"
#define MyTsVersion "1.104.1"
#define MyZhVersion "1.0.0"
#define MyPublisher "guoxpeng"
#define MyUrl       "https://github.com/guoxpeng/Tailscale"

[Setup]
AppId={{7C4E2A18-9B3D-4F52-8E61-5A0D3C9B7E24}
AppName={#MyZhName}
AppVersion={#MyTsVersion}
AppVerName={#MyZhName} {#MyTsVersion}
AppPublisher={#MyPublisher}
AppPublisherURL={#MyUrl}
AppSupportURL={#MyUrl}
AppUpdatesURL={#MyUrl}
VersionInfoVersion=1.104.1.0
VersionInfoProductName={#MyZhName}
VersionInfoCompany={#MyPublisher}
VersionInfoDescription={#MyZhName} 安装程序
DefaultDirName={commonpf}\Tailscale
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=Tailscale-zh-{#MyTsVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyZhName} {#MyTsVersion}
UninstallDisplayIcon={app}\tailscale-ipn.exe
SetupLogging=yes

[Languages]
; 官方未随安装包分发简中语言包，这里从 issrc 同版本 tag 取来放在同目录，保证编译期确定
Name: "chinese"; MessagesFile: "{#SourcePath}\ChineseSimplified.isl"

[Files]
; 汉化版先以 .new 落地，替换动作放在 [Code] 里做（要先备份原版）
Source: "..\build\tailscale-ipn.zh.exe"; DestDir: "{app}"; DestName: "tailscale-ipn.exe.new"; Flags: ignoreversion

[Code]
const
  EXE_NAME = 'tailscale-ipn.exe';
  BAK_NAME = 'tailscale-ipn.exe.orig';
  NEW_NAME = 'tailscale-ipn.exe.new';
  EXPECT_SIZE = 29622776;

function TsDir(): String;
begin
  Result := ExpandConstant('{commonpf}\Tailscale');
end;

function TsExe(): String;
begin
  Result := TsDir() + '\' + EXE_NAME;
end;

{ 结束正在运行的托盘 / 主界面程序，否则文件被占用 }
procedure KillTray();
var
  Rc: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM ' + EXE_NAME, '',
       SW_HIDE, ewWaitUntilTerminated, Rc);
  Sleep(800);
end;

{ 以「登录用户」身份启动托盘程序（而不是管理员身份） }
procedure StartTrayAsUser();
var
  Rc: Integer;
begin
  if not FileExists(TsExe()) then
    Exit;
  if not ShellExecAsUser('open', TsExe(), '', TsDir(), SW_SHOWNORMAL, ewNoWait, Rc) then
    Log('ShellExecAsUser 启动托盘失败，回退为 Exec');
end;

{ 替换主程序。Tailscale 可能自动把 GUI 拉起来重新占用文件，
  因此 kill 之后带重试，避免偶发失败。 }
function ReplaceExe(const Base, NewExe: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to 5 do
  begin
    KillTray();
    DeleteFile(Base);
    if RenameFile(NewExe, Base) then
    begin
      Result := True;
      Exit;
    end;
    if FileCopy(NewExe, Base, False) then
    begin
      DeleteFile(NewExe);
      Result := True;
      Exit;
    end;
    Log('第 ' + IntToStr(I) + ' 次替换失败（文件可能仍被占用），重试…');
    Sleep(1000);
  end;
end;

function InitializeSetup(): Boolean;
begin
  if not FileExists(TsExe()) then
  begin
    MsgBox('未检测到已安装的 Tailscale。' + #13#10 + #13#10 +
           '找不到文件:' + #13#10 + TsExe() + #13#10 + #13#10 +
           '请先安装官方 Tailscale {#MyTsVersion}（x64），再运行本汉化安装包。',
           mbCriticalError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Base, Bak, NewExe: String;
  Sz: Integer;
begin
  if CurStep <> ssPostInstall then
    Exit;

  Base   := TsExe();
  Bak    := TsDir() + '\' + BAK_NAME;
  NewExe := TsDir() + '\' + NEW_NAME;

  KillTray();

  { 只备份一次：保留最初那份官方原版，避免二次安装把汉化版当成「原版」备份 }
  if not FileExists(Bak) then
  begin
    if not FileCopy(Base, Bak, False) then
    begin
      MsgBox('备份原版 tailscale-ipn.exe 失败，安装中止。' + #13#10 +
             '请确认以管理员身份运行安装程序。', mbCriticalError, MB_OK);
      RaiseException('备份原版失败');
    end;
    Log('已备份原版 -> ' + Bak);
  end;

  if not FileExists(NewExe) then
  begin
    MsgBox('安装载荷缺失（tailscale-ipn.exe.new），安装中止。', mbCriticalError, MB_OK);
    RaiseException('缺少载荷文件');
  end;

  if not ReplaceExe(Base, NewExe) then
  begin
    MsgBox('写入汉化版 tailscale-ipn.exe 失败。' + #13#10 +
           '请手动退出 Tailscale 托盘程序后再试，或以管理员身份运行安装程序。',
           mbCriticalError, MB_OK);
    RaiseException('替换失败');
  end;

  Sz := FileSize(Base);
  if Sz <> EXPECT_SIZE then
    Log('警告: 安装后文件大小 ' + IntToStr(Sz) + '，预期 ' + IntToStr(EXPECT_SIZE));
  Log('汉化版已写入 ' + Base + '（' + IntToStr(Sz) + ' 字节）');

  StartTrayAsUser();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Base, Bak: String;
begin
  if CurUninstallStep <> usUninstall then
    Exit;

  Base := TsExe();
  Bak  := TsDir() + '\' + BAK_NAME;
  if not FileExists(Bak) then
  begin
    Log('未找到备份 ' + Bak + '，跳过还原');
    Exit;
  end;

  KillTray();
  DeleteFile(Base);
  if RenameFile(Bak, Base) then
    Log('已还原官方 tailscale-ipn.exe')
  else
    MsgBox('还原官方 tailscale-ipn.exe 失败。' + #13#10 +
           '请手动把 ' + Bak + ' 改名为 ' + Base + '。', mbError, MB_OK);

  StartTrayAsUser();
end;
