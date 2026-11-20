; Instalador de Traductor en Vivo (Inno Setup 6)
; Compilar:  ISCC.exe /DAppVersion=1.0.0 installer\setup.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Traductor en Vivo"
#define AppExe "TraductorEnVivo.exe"

[Setup]
AppId={{6F1C2B8E-3A47-4E59-9C1D-7B2E5A0F4D11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=SoupOfMacaco
AppPublisherURL=https://github.com/SoupOfMacaco/traductor-en-vivo
AppSupportURL=https://github.com/SoupOfMacaco/traductor-en-vivo/issues
AppUpdatesURL=https://github.com/SoupOfMacaco/traductor-en-vivo/releases
DefaultDirName={autopf}\TraductorEnVivo
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Se instala solo para el usuario actual: no pide administrador y se puede actualizar en silencio
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=TraductorEnVivo-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
AppMutex=TraductorEnVivoMutex
CloseApplications=force
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "autostart"; Description: "Iniciar con Windows"; GroupDescription: "Opciones:"; Flags: unchecked

[Files]
Source: "..\dist\TraductorEnVivo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Borra los archivos de la versión anterior para que no queden restos
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "TraductorEnVivo"; ValueData: """{app}\{#AppExe}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Sin "skipifsilent": tras una actualización automática (/SILENT) la app se vuelve a abrir sola
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#AppExe} /F"; Flags: runhidden; RunOnceId: "KillApp"
