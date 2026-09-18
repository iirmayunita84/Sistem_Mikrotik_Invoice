#define MyAppName "Mikrotik Invoice"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Unite Software"
#define MyAppExeName "mikrotik_invoice.exe"

[Setup]
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoTextVersion={#MyAppVersion}

AppId={{A1B2C3D4-1111-2222-3333-444455556666}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\Mikrotik Invoice
DefaultGroupName=Mikrotik Invoice

OutputDir=output
OutputBaseFilename=Setup_Mikrotik_Invoice
Compression=lzma
SolidCompression=yes

SetupIconFile=icon.ico
WizardImageFile=splash.bmp
WizardSmallImageFile=small.bmp


PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

DisableProgramGroupPage=yes
DisableWelcomePage=no
Uninstallable=yes

AllowNoIcons=yes
CloseApplications=yes
RestartApplications=no


[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\mikrotik_invoice.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\uninstall_guard.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}";
Description: "Jalankan {#MyAppName}";
Flags: nowait postinstall skipifsilent runasoriginaluser


[Code]

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;

  if not FileExists(ExpandConstant('{app}\uninstall_guard.exe')) then
  begin
    MsgBox('Uninstall guard tidak ditemukan.', mbError, MB_OK);
    Exit;
  end;

  Exec(
    ExpandConstant('{app}\uninstall_guard.exe'),
    '',
    '',
    SW_SHOW,
    ewWaitUntilTerminated,
    ResultCode
  );

  if ResultCode = 0 then
    Result := True
  else
    MsgBox('Uninstall dibatalkan oleh sistem.', mbInformation, MB_OK);
end;


