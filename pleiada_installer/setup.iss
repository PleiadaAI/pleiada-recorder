; Pleiada Recorder - Inno Setup Script
; Genera: PleiadaRecorder_Setup.exe

#define AppName    "Pleiada Recorder"
#define AppVersion "0.25"
#define AppPublisher "Pleiada"
#define AppDir     "{autopf}\Pleiada Recorder"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={#AppDir}
DefaultGroupName={#AppName}
OutputBaseFilename=PleiadaRecorder_Setup
OutputDir=Output
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\pleiada.ico
SetupIconFile=assets\pleiada.ico
WizardImageFile=assets\wizard_banner.bmp
WizardSmallImageFile=assets\wizard_small.bmp
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
spanish.InstallingPython=Instalando Python... (esto puede tardar varios minutos, por favor espera)
spanish.InstallingAHK=Instalando AutoHotkey...
spanish.InstallingOBS=Instalando OBS Studio - complete el asistente que aparece en pantalla...
spanish.InstallingDeps=Instalando dependencias...
spanish.ConfiguringOBS=Configurando OBS...
spanish.AllDone=Instalacion completada. Ya podes usar Pleiada Recorder.

[Files]
; Scripts principales
Source: "files\gameplay_logger.ahk";      DestDir: "{app}"; Flags: ignoreversion
Source: "files\obs_control.py";          DestDir: "{app}"; Flags: ignoreversion
Source: "files\pleiada_check.pyw";       DestDir: "{app}"; Flags: ignoreversion
Source: "files\pleiada_setup_wizard.pyw"; DestDir: "{app}"; Flags: ignoreversion
; Instaladores de dependencias
Source: "deps\python-3.12.8-amd64.exe";                       DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "deps\AutoHotkey_2.0.24_setup.exe";                   DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "deps\OBS-Studio-32.1.2-Windows-x64-Installer.exe";   DestDir: "{tmp}"; Flags: deleteafterinstall
; Script de configuracion de OBS WebSocket
Source: "files\configure_obs.py"; DestDir: "{tmp}"; Flags: deleteafterinstall
; Iconos
Source: "assets\pleiada.ico";        DestDir: "{app}"; Flags: ignoreversion
Source: "assets\synch_checker.ico";  DestDir: "{app}"; Flags: ignoreversion
; Logo Pleiada (usado por el Synch Checker)
Source: "assets\pleiada_icon.png";   DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commondesktop}\Pleiada Recorder"; \
    Filename: "{app}\gameplay_logger.ahk"; \
    IconFilename: "{app}\pleiada.ico"; \
    Comment: "Iniciar grabacion de gameplay"
Name: "{commondesktop}\Synch Checker"; \
    Filename: "{code:FindPythonW}"; \
    Parameters: """{app}\pleiada_check.pyw"""; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\synch_checker.ico"; \
    Comment: "Verificar sincronizacion de grabacion"

[Run]
; 1. Instalar Python (silencioso, solo si no esta instalado)
Filename: "{tmp}\python-3.12.8-amd64.exe"; \
    Parameters: "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0"; \
    StatusMsg: "{cm:InstallingPython}"; \
    Check: not PythonInstalled

; 2. Instalar AutoHotkey v2
Filename: "{tmp}\AutoHotkey_2.0.24_setup.exe"; \
    StatusMsg: "{cm:InstallingAHK}"; \
    Flags: waituntilterminated

; 3. Cerrar OBS si esta abierto y necesita ser actualizado
Filename: "taskkill"; \
    Parameters: "/F /IM obs64.exe"; \
    Flags: runhidden; \
    Check: OBSRunning and OBSNeedsInstall

; 4. Instalar OBS solo si no esta instalado o version es menor a la requerida
Filename: "{tmp}\OBS-Studio-32.1.2-Windows-x64-Installer.exe"; \
    StatusMsg: "{cm:InstallingOBS}"; \
    Flags: waituntilterminated; \
    Check: OBSNeedsInstall

; 4.5. Cerrar OBS si fue lanzado por su propio instalador
Filename: "{sys}\taskkill.exe"; \
    Parameters: "/F /IM obs64.exe"; \
    Flags: runhidden; \
    Check: OBSNeedsInstall

; 5. Instalar dependencias Python via pip
Filename: "python"; \
    Parameters: "-m pip install websocket-client Pillow opencv-python --quiet"; \
    StatusMsg: "{cm:InstallingDeps}"; \
    Flags: runhidden

; 6. Configurar OBS WebSocket automaticamente
Filename: "python"; \
    Parameters: """{tmp}\configure_obs.py"""; \
    StatusMsg: "{cm:ConfiguringOBS}"; \
    Flags: runhidden

; 7. Wizard de configuracion inicial — se lanza automaticamente (sin checkbox)
Filename: "{app}\pleiada_setup_wizard.pyw"; \
    StatusMsg: "{cm:AllDone}"; \
    Flags: nowait shellexec

[Code]

var
  ConsentPage:  TWizardPage;
  ConsentMemo:  TNewMemo;
  ConsentCheck: TNewCheckBox;

procedure InitializeWizard;
begin
  ConsentPage := CreateCustomPage(
    wpWelcome,
    'Bienvenido a Pleiada Recorder - Gameplay Alliance',
    'Lee atentamente la siguiente informacion antes de continuar.'
  );

  ConsentMemo := TNewMemo.Create(ConsentPage);
  ConsentMemo.Parent   := ConsentPage.Surface;
  ConsentMemo.Left     := 0;
  ConsentMemo.Top      := 0;
  ConsentMemo.Width    := ConsentPage.SurfaceWidth;
  ConsentMemo.Height   := ConsentPage.SurfaceHeight - 60;
  ConsentMemo.ReadOnly := True;
  ConsentMemo.ScrollBars := ssVertical;
  ConsentMemo.Color    := $F8F6FF;
  ConsentMemo.Lines.Add('Bienvenidos al Gameplay Alliance!');
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    'Pleiada Recorder es una herramienta desarrollada por Pleiada para el programa ' +
    'Gameplay Alliance. Esta construida exclusivamente sobre bibliotecas de codigo ' +
    'abierto y es completamente segura de instalar y utilizar.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add('QUE INSTALA ESTE PROGRAMA:');
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    '- AutoHotkey v2 (https://www.autohotkey.com/)' + #13#10 +
    '  Software libre de codigo abierto que registra de forma anonimizada ' +
    'la actividad del teclado y del mouse durante la sesion de grabacion.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    '- OBS Studio (https://obsproject.com/)' + #13#10 +
    '  Software libre de codigo abierto para grabar la pantalla durante el gameplay.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add('SOBRE LOS DATOS RECOPILADOS:');
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    'Toda la informacion recopilada por este software es y debe ser estrictamente ' +
    'anonima. No se almacena ni transmite ningun dato de identificacion personal.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    'Al continuar con la instalacion, confirmas que has leido y firmado los ' +
    'terminos y condiciones, que sos mayor de edad y que participas ' +
    'voluntariamente en el programa.'
  );

  ConsentCheck := TNewCheckBox.Create(ConsentPage);
  ConsentCheck.Parent  := ConsentPage.Surface;
  ConsentCheck.Left    := 0;
  ConsentCheck.Top     := ConsentPage.SurfaceHeight - 54;
  ConsentCheck.Width   := ConsentPage.SurfaceWidth;
  ConsentCheck.Height  := 54;
  ConsentCheck.Caption := 'Acepto los terminos y condiciones del programa. (pleiada.ai/terms)';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ConsentPage.ID then
  begin
    if not ConsentCheck.Checked then
    begin
      MsgBox(
        'Debes marcar la casilla para confirmar que has leido los terminos y condiciones antes de continuar.',
        mbError,
        MB_OK
      );
      Result := False;
    end;
  end;
end;

function PythonInstalled: Boolean;
begin
  Result := RegKeyExists(HKCU, 'Software\Python\PythonCore\3.12');
  if not Result then
    Result := RegKeyExists(HKLM, 'Software\Python\PythonCore\3.12');
end;

{ Devuelve la ruta completa a pythonw.exe para el shortcut del Synch Checker }
function FindPythonW(Param: String): String;
var
  PythonDir: String;
begin
  Result := 'pythonw.exe'; { fallback si no se encuentra por registro }

  { Python instalado per-user (InstallAllUsers=0 — nuestro caso) }
  if RegQueryStringValue(HKCU,
      'Software\Python\PythonCore\3.12\InstallPath', '', PythonDir) then
  begin
    if (Length(PythonDir) > 0) and (PythonDir[Length(PythonDir)] <> '\') then
      PythonDir := PythonDir + '\';
    if FileExists(PythonDir + 'pythonw.exe') then
    begin
      Result := PythonDir + 'pythonw.exe';
      Exit;
    end;
  end;

  { Python instalado para todos los usuarios }
  if RegQueryStringValue(HKLM,
      'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', PythonDir) then
  begin
    if (Length(PythonDir) > 0) and (PythonDir[Length(PythonDir)] <> '\') then
      PythonDir := PythonDir + '\';
    if FileExists(PythonDir + 'pythonw.exe') then
      Result := PythonDir + 'pythonw.exe';
  end;
end;

function OBSInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{autopf}\obs-studio\bin\64bit\obs64.exe'));
end;

{ Devuelve True si OBS no esta instalado o si la version instalada es menor a 32.1.2 }
function OBSNeedsInstall: Boolean;
var
  ExePath: String;
  MS, LS: Cardinal;
  Major, Minor, Patch: Cardinal;
begin
  Result := True; { instalar por defecto }
  ExePath := ExpandConstant('{autopf}\obs-studio\bin\64bit\obs64.exe');
  if not FileExists(ExePath) then Exit; { no instalado → instalar }
  if not GetVersionNumbers(ExePath, MS, LS) then Exit; { no se pudo leer version → instalar }

  Major := MS shr 16;
  Minor := MS and $FFFF;
  Patch := LS shr 16;

  { Requerido: 32.1.2 — si instalado >= 32.1.2, no instalar }
  if Major > 32 then Result := False
  else if (Major = 32) and (Minor > 1) then Result := False
  else if (Major = 32) and (Minor = 1) and (Patch >= 2) then Result := False;
end;

function OBSRunning: Boolean;
var
  RC: Integer;
begin
  Exec('tasklist', '/FI "IMAGENAME eq obs64.exe" /NH', '', SW_HIDE,
       ewWaitUntilTerminated, RC);
  Result := (RC = 0);
end;































