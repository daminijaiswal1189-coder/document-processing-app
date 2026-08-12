; Inno Setup script — optional installer around POC-UI.exe
; 1. Install Inno Setup: https://jrsoftware.org/isinfo.php
; 2. Run desktop\build-windows.bat first
; 3. Open this file in Inno Setup Compiler → Build
; Output: desktop\installer\POC-UI-Setup.exe
;
; True .msi needs WiX Toolset; for most demos Setup.exe is enough.

#define MyAppName "Document Processing POC UI"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "POC"
#define MyAppExeName "POC-UI.exe"

[Setup]
AppId={{A1B2C3D4-POC1-4UI2-9E0F-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\POC-UI
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=POC-UI-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x86 x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Entire onedir build from PyInstaller
Source: "dist\POC-UI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
