#define MyAppName "南极科研图谱"
#define MyAppVersion "3.1.2"
#define MyAppPublisher "Omica Chow"
#define MyAppExeName "Antarctic Atlas ZH.exe"
#define SourceAppDir "..\dist\Antarctic Atlas ZH"
#define OutputDir "..\..\Installers"

[Setup]
AppId={{7F3B1174-7425-43AD-B59C-9CF5A7E7F8B2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=Antarctic-Atlas-ZH-v{#MyAppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=antarctic_atlas.ico
WizardImageFile=wizard_side.bmp
WizardSmallImageFile=wizard_small.bmp
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UsedUserAreasWarning=no
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Antarctic Atlas Chinese Windows Installer
VersionInfoProductName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal\streamlit"
Type: filesandordirs; Name: "{app}\_internal\atlas_app"
Type: filesandordirs; Name: "{app}\app.py"

[Files]
Source: "{#SourceAppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,atlas_desktop.log,.streamlit\secrets.toml"
Source: "antarctic_atlas.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\antarctic_atlas.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\antarctic_atlas.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel1.Caption := '欢迎使用南极科研图谱';
  WizardForm.WelcomeLabel2.Caption := '安装南极冰盖科研图谱桌面应用。你可以用交互式科研宇宙、液态玻璃风格可视模块和 AI 问答探索综述论文。';
end;
