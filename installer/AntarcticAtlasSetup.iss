#define MyAppName "Antarctic Atlas"
#define MyAppVersion "2.0.5"
#define MyAppPublisher "Omica Chow"
#define MyAppExeName "Antarctic Atlas.exe"
#define SourceAppDir "C:\Users\Omica\Desktop\Antarctic Atlas App"
#define OutputDir "C:\Users\Omica\Desktop"

[Setup]
AppId={{9C7E95BA-2B59-44E1-A40A-95B62A3C9978}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=Antarctic-Atlas-v{#MyAppVersion}-Setup
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
VersionInfoDescription=Antarctic Atlas Windows Installer
VersionInfoProductName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "{#SourceAppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc,atlas_desktop.log,.streamlit\secrets.toml"
Source: "antarctic_atlas.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\antarctic_atlas.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\antarctic_atlas.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel1.Caption := 'Welcome to Antarctic Atlas';
  WizardForm.WelcomeLabel2.Caption := 'Install the Antarctic Ice Sheet Research Atlas desktop app. Explore the review paper as an interactive research universe with liquid-glass visual modules.';
end;
