#define MyAppName "Sistem Mikrotik Invoice"
#define MyAppVersion "1.0"
#define MyAppPublisher "YUNITA"
#define MyAppExeName "main.exe"

[Setup]
AppId={{C5F3A8F2-1234-4A3E-92D3-91F52D7A1111}}
AppName=Sistem Mikrotik Invoice
AppVersion=1.0
AppPublisher={#MyAppPublisher}
DefaultDirName={pf32}\Sistem Mikrotik Invoice
DefaultGroupName=Sistem Mikrotik Invoice
OutputDir=Output
OutputBaseFilename=Sistem_Mikrotik_Invoice_Installer
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableDirPage=no
DisableProgramGroupPage=no
SetupIconFile=D:\Sistem_Mikrotik_Invoice\assets\icon.ico
UninstallDisplayIcon={app}\assets\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut:"

[Files]
Source: "D:\Sistem_Mikrotik_Invoice\dist\main\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
Source: "poppler\*"; DestDir: "{app}\poppler"; Flags: recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs createallsubdirs
Source: "riwayat_invoice\*"; DestDir: "{app}\riwayat_invoice"; Flags: recursesubdirs createallsubdirs
Source: "config.json"; DestDir: "{app}"

[Icons]
Name: "{commondesktop}\Sistem Mikrotik Invoice"; Filename: "{app}\main.exe"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Sistem Mikrotik Invoice"; Filename: "{app}\main.exe"; IconFilename: "{app}\assets\icon.ico"

[Run]
Filename: "{app}\main.exe"; Description: "Jalankan Sistem Mikrotik Invoice"; Flags: nowait postinstall skipifsilent
