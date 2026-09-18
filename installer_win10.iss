#define MyAppName "Mikrotik Invoice"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Unite Software"
#define MyAppExeName "MikrotikInvoice_Win10.exe"

[Setup]
AppId={{8B8E7D51-4D72-4C8D-9A37-1F4E6D8B9210}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\MikrotikInvoice
DefaultGroupName={#MyAppName}

OutputDir=installer_win10
OutputBaseFilename=MikrotikInvoice_Win10_Setup

Compression=lzma
SolidCompression=yes

WizardStyle=modern

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

DisableProgramGroupPage=yes

SetupIconFile=assets\Untitled.ico

UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist_win10\MikrotikInvoice_Win10\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"

Name: "{commondesktop}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Flags: nowait postinstall skipifsilent runasoriginaluser