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
; 唯一被替换的文件（托盘 / 主界面程序）。全脚本只在这里定义一次。
#define ExeName     "tailscale-ipn.exe"
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
UninstallDisplayIcon={app}\{#ExeName}
SetupLogging=yes

[Languages]
; 官方未随安装包分发简中语言包，这里从 issrc 同版本 tag 取来放在同目录，保证编译期确定
Name: "chinese"; MessagesFile: "{#SourcePath}\ChineseSimplified.isl"

[Files]
; 汉化版先以 .new 落地，替换动作放在 [Code] 里做（要先备份原版）
Source: "..\build\tailscale-ipn.zh.exe"; DestDir: "{app}"; DestName: "{#ExeName}.new"; Flags: ignoreversion

[Code]
const
  EXE_NAME = '{#ExeName}';
  BAK_NAME = '{#ExeName}.orig';
  NEW_NAME = '{#ExeName}.new';
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

{ 以「登录用户」身份启动托盘程序（而不是管理员身份）。
  注意：Inno 里没有 ShellExecAsUser 这个脚本函数，正确的是 ExecAsOriginalUser。
  **本函数只能在安装阶段调用** —— ExecAsOriginalUser 在卸载阶段会抛致命错误
  "Cannot call ExecAsOriginalUser function during Uninstall"，
  因此卸载流程不会拉起托盘（原因详见 CurUninstallStepChanged 末尾）。 }
procedure StartTrayAsUser();
var
  Rc: Integer;
begin
  if not FileExists(TsExe()) then
    Exit;
  if ExecAsOriginalUser(TsExe(), '', TsDir(), SW_SHOWNORMAL, ewNoWait, Rc) then
    Exit;
  Log('ExecAsOriginalUser 启动托盘失败，回退为 Exec');
  if not Exec(TsExe(), '', TsDir(), SW_SHOWNORMAL, ewNoWait, Rc) then
    Log('启动 Tailscale 托盘程序失败，请手动运行 ' + TsExe());
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
    if CopyFile(NewExe, Base, False) then
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
    if not CopyFile(Base, Bak, False) then
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
    { 兜底：ReplaceExe 会先删掉原 exe，一旦替换失败，用户机器上就没有主程序了。
      此时把备份还原回去，至少保证 Tailscale 仍可用。 }
    if FileExists(Bak) and RenameFile(Bak, Base) then
      Log('替换失败，已自动还原官方原版 -> ' + Base);
    MsgBox('写入汉化版 tailscale-ipn.exe 失败。' + #13#10 +
           '请手动退出 Tailscale 托盘程序后再试，或以管理员身份运行安装程序。',
           mbCriticalError, MB_OK);
    RaiseException('替换失败');
  end;

  { Inno 的 FileSize 是「var 出参 + Boolean 返回」，不是返回值函数 }
  if not FileSize(Base, Sz) then
  begin
    Sz := -1;
    Log('警告: 读取 ' + Base + ' 大小失败');
  end;
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
    Log('已还原官方 ' + EXE_NAME)
  else
    MsgBox('还原官方 ' + EXE_NAME + ' 失败。' + #13#10 +
           '请手动把 ' + Bak + ' 改名为 ' + Base + '。', mbError, MB_OK);

  { 这里刻意**不**再拉起托盘程序，原因有两条：
      1) ExecAsOriginalUser 在卸载阶段会抛致命异常
         （Runtime error: Cannot call "ExecAsOriginalUser" function during Uninstall）；
      2) Inno 的 [UninstallRun] 段不支持 runasoriginaluser，只支持 runascurrentuser，
         而卸载器此时已经提权，用它拉起会让 Tailscale GUI 以管理员身份运行
         （Tailscale 官方不支持 GUI 提权运行）。
    托盘由用户从开始菜单重新打开即可，tailscaled 服务与官方程序都不受影响。 }
  Log('汉化已卸下，官方版已还原；托盘程序已退出，可从开始菜单重新打开 Tailscale。');
end;
