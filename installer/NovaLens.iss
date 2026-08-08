#define MyAppName "Nova Lens"
#ifndef MyAppVersion
#define MyAppVersion "2.0.1"
#endif
#define MyAppPublisher "Nova Lens"
#define MyAppURL "https://github.com/uryastra-beep/NovaLens"
#define MyAppSupportURL "https://discord.gg/Dfns48WEqH"
#define MyAppExeName "NovaLens.exe"

[Setup]
AppId={{5C543248-79D7-4F74-8AC9-B1E9521A7A20}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupportURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\Nova Lens
DefaultGroupName=Nova Lens
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer-output
OutputBaseFilename=NovaLens-Setup-v{#MyAppVersion}-Windows-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Nova Lens Windows installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
#if FileExists("..\assets\NovaLens.ico")
SetupIconFile=..\assets\NovaLens.ico
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\NovaLens\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Nova Lens"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Nova Lens"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM NovaLens.exe /T /F >NUL 2>&1"; Flags: runhidden; RunOnceId: "StopNovaLens"
