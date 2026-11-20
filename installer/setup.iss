; Instalador de Glosa (Inno Setup 6)
; Compilar:  ISCC.exe /DAppVersion=1.1.0 installer\setup.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Glosa"
#define AppExe "Glosa.exe"
#define Repo "https://github.com/SoupOfMacaco/glosa"

[Setup]
; El AppId no cambia nunca: así la 1.0.0 ("Traductor en Vivo") se actualiza a Glosa en vez de instalarse dos veces
AppId={{6F1C2B8E-3A47-4E59-9C1D-7B2E5A0F4D11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=SoupOfMacaco
AppPublisherURL={#Repo}
AppSupportURL={#Repo}/issues
AppUpdatesURL={#Repo}/releases
DefaultDirName={autopf}\Glosa
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UsePreviousGroup=no
; Se instala solo para el usuario actual: no pide administrador y se puede actualizar en silencio
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=Glosa-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
; Muestra la licencia (uso no comercial) y hay que aceptarla para instalar. Las actualizaciones silenciosas no la muestran.
LicenseFile=..\LICENSE
AppCopyright=Copyright (c) 2026 SoupOfMacaco. Uso no comercial (PolyForm Noncommercial 1.0.0).
WizardSmallImageFile=..\assets\wizard-small.bmp
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
AppMutex=GlosaMutex,TraductorEnVivoMutex
CloseApplications=force
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "englishocr"; Description: "Instalar el OCR en inglés de Windows (lee mucho mejor el inglés; pedirá permiso de administrador una vez)"; GroupDescription: "Recomendado:"; Check: NeedsEnglishOcr
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "autostart"; Description: "Iniciar con Windows"; GroupDescription: "Opciones:"; Flags: unchecked

[Files]
Source: "..\dist\Glosa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Borra los archivos de la versión anterior para que no queden restos
Type: filesandordirs; Name: "{app}\_internal"
; Restos de la 1.0.0, cuando la app se llamaba "Traductor en Vivo"
Type: files; Name: "{app}\TraductorEnVivo.exe"
Type: files; Name: "{autodesktop}\Traductor en Vivo.lnk"
Type: filesandordirs; Name: "{autoprograms}\Traductor en Vivo"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Traductor en vivo para juegos"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "TraductorEnVivo"; Flags: deletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Glosa"; ValueData: """{app}\{#AppExe}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; El OCR en inglés es un componente de Windows: solo se puede añadir como administrador, así que se pide permiso solo para este paso
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ""Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'"""; Verb: "runas"; Flags: shellexec waituntilterminated runhidden; StatusMsg: "Instalando el OCR en inglés de Windows (puede tardar un par de minutos)..."; Tasks: englishocr
; Sin "skipifsilent": tras una actualización automática (/SILENT) la app se vuelve a abrir sola
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#AppExe} /F"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
function NeedsEnglishOcr: Boolean;
begin
  { Las actualizaciones automáticas son silenciosas: no deben pedir permisos de administrador }
  Result := (not WizardSilent) and
            (not DirExists(ExpandConstant('{win}\OCR\en-us'))) and
            (not DirExists(ExpandConstant('{win}\OCR\en-gb')));
end;
