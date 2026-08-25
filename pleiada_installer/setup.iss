; Gameplay Recorder - Inno Setup Script
; Los .exe de salida conservan el nombre PleiadaRecorder_*: el site linkea al
; permalink releases/latest/download/PleiadaRecorder_Setup.exe.
; Genera dos instaladores a partir del mismo script:
;   - PleiadaRecorder_Setup.exe   (completo: app + Python + AHK + OBS)      → iscc setup.iss
;   - PleiadaRecorder_Update.exe  (LITE: solo archivos de la app, updater)  → iscc /DLITE setup.iss
; La version se inyecta desde CI con /DAppVersion=X.Y.Z (fallback abajo para builds locales).

#define AppName    "Gameplay Recorder"
; AppId NO acompaña al rename: es la identidad de la instalación. Si cambia, el
; updater LITE deja de reconocer la instalación existente y monta una segunda en
; paralelo, con dos entradas en Programas y dos carpetas. Queda clavado al valor
; histórico para siempre.
#define AppId      "Pleiada Recorder"
#ifndef AppVersion
  #define AppVersion "0.7.0"
#endif
#define AppPublisher "Sunrise Advisors Generation Ltd"
; Solo afecta a instalaciones NUEVAS: en un upgrade Inno reusa la carpeta que ya
; registró bajo el mismo AppId, así que los usuarios actuales siguen en la suya.
#define AppDir     "{autopf}\Gameplay Recorder"
; Paquetes pip de la app — mantener UNA sola lista para full y update
#define PipPackages "websocket-client Pillow opencv-python"

[Setup]
; AppId explicito (= el nombre historico "Pleiada Recorder", NO el nombre
; visible actual) para que el updater LITE actualice la MISMA entrada instalada
; y no cree una instalacion paralela.
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={#AppDir}
DefaultGroupName={#AppName}
#ifdef LITE
OutputBaseFilename=PleiadaRecorder_Update
; El updater no pregunta nada: directo a copiar (ademas se lanza /SILENT desde la app)
DisableDirPage=yes
DisableReadyPage=yes
DisableFinishedPage=yes
#else
OutputBaseFilename=PleiadaRecorder_Setup
#endif
OutputDir=Output
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\gameplay_recorder.ico
SetupIconFile=assets\gameplay_recorder.ico
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
spanish.AllDone=Instalacion completada. Ya podes usar Gameplay Recorder.

[Files]
; Scripts principales
Source: "files\pleiada_app.pyw";          DestDir: "{app}"; Flags: ignoreversion
Source: "files\session_uploader.py";      DestDir: "{app}"; Flags: ignoreversion
Source: "files\pleiada_api.py";           DestDir: "{app}"; Flags: ignoreversion
Source: "files\pleiada_sync_limits.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "files\obs_encoding.py";          DestDir: "{app}"; Flags: ignoreversion
Source: "files\input_logger.ahk";         DestDir: "{app}"; Flags: ignoreversion
Source: "files\obs_control.py";           DestDir: "{app}"; Flags: ignoreversion
Source: "files\pleiada_setup_wizard.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "files\pleiada_check.pyw";        DestDir: "{app}"; Flags: ignoreversion
Source: "files\games_list.json";          DestDir: "{app}"; Flags: ignoreversion
#ifndef LITE
; Instaladores de dependencias (solo instalador completo)
Source: "deps\python-3.12.8-amd64.exe";                       DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "deps\AutoHotkey_2.0.24_setup.exe";                   DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "deps\OBS-Studio-32.1.2-Windows-x64-Installer.exe";   DestDir: "{tmp}"; Flags: deleteafterinstall
#endif
; Configuracion de OBS. VA TAMBIEN EN EL LITE: es la unica via por la que un
; usuario ya instalado recibe RecQuality/RecEncoder, y el auto-update usa el
; LITE. Dejandolo solo en el completo, la flota actual seguiria grabando 1080p60
; a 2,5 Mbps para siempre (medido: 135 de 166 sesiones del test de 100h).
Source: "files\configure_obs.py"; DestDir: "{tmp}"; Flags: deleteafterinstall
; configure_obs.py importa obs_encoding, y corre desde {tmp}: si el modulo no
; viaja al lado, el import falla y el perfil queda sin la config de grabacion.
; Va ademas a {app}, que es de donde lo levanta la app al grabar.
Source: "files\obs_encoding.py";  DestDir: "{tmp}"; Flags: deleteafterinstall
; Iconos
Source: "assets\gameplay_recorder.ico";        DestDir: "{app}"; Flags: ignoreversion
Source: "assets\synch_checker.ico";  DestDir: "{app}"; Flags: ignoreversion
; Logo Gameplay Alliance (usado por el Synch Checker)
Source: "assets\gameplay_recorder_icon.png";   DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; Al actualizar desde una versión anterior al rename queda el acceso directo con
; el nombre viejo apuntando a la misma app. Sin esto, el usuario ve dos.
Type: files; Name: "{commondesktop}\Pleiada Recorder.lnk"

[Icons]
Name: "{commondesktop}\{#AppName}"; \
    Filename: "{code:FindPythonW}"; \
    Parameters: """{app}\pleiada_app.pyw"""; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\gameplay_recorder.ico"; \
    Comment: "{#AppName} v{#AppVersion} — Gameplay Alliance"

; Nota: el Synch Checker se ejecuta automáticamente desde el Recorder (sin shortcut en escritorio)

[Run]
#ifndef LITE
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
#endif

; 5. Instalar dependencias Python via pip (ruta absoluta para evitar problemas de PATH)
;    Tambien corre en el updater LITE: si una version nueva suma un paquete a
;    PipPackages, la base instalada lo recibe con el update (no-op si ya estan).
Filename: "{code:FindPythonExe}"; \
    Parameters: "-m pip install {#PipPackages} --quiet"; \
    StatusMsg: "{cm:InstallingDeps}"; \
    Flags: runhidden waituntilterminated

; 6. Configurar OBS (WebSocket + perfil). Corre en AMBOS instaladores: en el
;    LITE es lo que migra el perfil preexistente a la config de grabacion nueva
;    (calidad constante con techo, encoder por hardware) — y de hecho es la via
;    principal, porque la app solo puede corregir la config con OBS cerrado o
;    reiniciandolo. Es idempotente y respeta la config del usuario salvo las
;    claves no negociables, asi que correrlo en cada update es seguro.
;    OJO: NO es RecQuality=HQ. En el .ini de OBS 'HQ' es la opcion MAS pesada
;    (CQP 16, "archivo grande"); los valores reales viven en obs_encoding.py.
Filename: "{code:FindPythonExe}"; \
    Parameters: """{tmp}\configure_obs.py"""; \
    StatusMsg: "{cm:ConfiguringOBS}"; \
    Flags: runhidden waituntilterminated

#ifndef LITE
; 7. Tutorial web — v0.8.4: reemplaza a las ventanas del wizard local.
;    Se abre en el browser por defecto del usuario (runasoriginaluser: sin elevar).
Filename: "https://recorder.gameplayalliance.gg/"; \
    StatusMsg: "{cm:AllDone}"; \
    Flags: nowait shellexec runasoriginaluser
#endif

#ifdef LITE
; LITE: relanzar el Recorder al terminar de actualizar, con las credenciales
; ORIGINALES del usuario (no elevado — el updater corre con UAC/admin).
Filename: "{code:FindPythonW}"; \
    Parameters: """{app}\pleiada_app.pyw"""; \
    WorkingDir: "{app}"; \
    Flags: nowait shellexec runasoriginaluser
#endif

[UninstallRun]
; Cerrar el Recorder si está abierto al desinstalar.
; Se matan LOS DOS títulos: el actual y el histórico "Pleiada Recorder", porque
; una instalación vieja sin actualizar todavía usa el nombre anterior.
Filename: "{sys}\taskkill.exe"; \
    Parameters: "/F /FI ""WINDOWTITLE eq {#AppName}"""; \
    Flags: runhidden; \
    RunOnceId: "KillRecorder"
Filename: "{sys}\taskkill.exe"; \
    Parameters: "/F /FI ""WINDOWTITLE eq Pleiada Recorder"""; \
    Flags: runhidden; \
    RunOnceId: "KillRecorderLegacy"

[Code]

{ Cerrar el Recorder si esta abierto, justo antes de copiar archivos.
  Necesario en el updater (la app se cierra sola antes de lanzarlo, esto es
  cinturon y tiradores) y util en el instalador completo al hacer upgrades.

  OJO: se matan LOS DOS titulos. Al actualizar desde una version anterior al
  rename, la app que esta corriendo todavia se titula "Pleiada Recorder"; si
  solo filtraramos por el titulo nuevo no la encontrariamos y los archivos
  quedarian bloqueados al copiar. }
{ FindPythonExe / FindPythonW van ANTES de CurStepChanged a proposito: el
  Pascal Script de Inno no admite referencias adelantadas, y CurStepChanged
  llama a FindPythonW para reparar el acceso directo despues de [Run]. }
{ Devuelve la ruta completa a python.exe para ejecutar pip y scripts }
function FindPythonExe(Param: String): String;
var
  PythonDir: String;
begin
  Result := 'python.exe'; { fallback si no se encuentra por registro }

  { Python instalado per-user (InstallAllUsers=0 — nuestro caso) }
  if RegQueryStringValue(HKCU,
      'Software\Python\PythonCore\3.12\InstallPath', '', PythonDir) then
  begin
    if (Length(PythonDir) > 0) and (PythonDir[Length(PythonDir)] <> '\') then
      PythonDir := PythonDir + '\';
    if FileExists(PythonDir + 'python.exe') then
    begin
      Result := PythonDir + 'python.exe';
      Exit;
    end;
  end;

  { Python instalado para todos los usuarios }
  if RegQueryStringValue(HKLM,
      'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', PythonDir) then
  begin
    if (Length(PythonDir) > 0) and (PythonDir[Length(PythonDir)] <> '\') then
      PythonDir := PythonDir + '\';
    if FileExists(PythonDir + 'python.exe') then
      Result := PythonDir + 'python.exe';
  end;
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


procedure CurStepChanged(CurStep: TSetupStep);
var
  RC: Integer;
  PyW: String;
begin
  if CurStep = ssInstall then
  begin
    Exec(ExpandConstant('{sys}\taskkill.exe'),
         '/F /FI "WINDOWTITLE eq {#AppName}"', '',
         SW_HIDE, ewWaitUntilTerminated, RC);
    Exec(ExpandConstant('{sys}\taskkill.exe'),
         '/F /FI "WINDOWTITLE eq Pleiada Recorder"', '',
         SW_HIDE, ewWaitUntilTerminated, RC);
  end;

  { ── Re-crear el acceso directo con la ruta real de pythonw.exe ──────────
    Inno procesa [Icons] ANTES que [Run], y es [Run] el que instala Python.
    En una maquina sin Python 3.12, FindPythonW no encuentra nada en el
    registro y cae al literal 'pythonw.exe', sin ruta: el acceso directo
    queda apuntando a un ejecutable que Windows no puede resolver y al
    abrirlo sale "Falta el acceso directo — Windows esta buscando
    pythonw.exe". Reinstalar no lo arregla si Python nunca llega a
    registrarse, porque el orden es siempre el mismo.

    Reportado el 25-08-2026 sobre la v0.9.10, tras desinstalar y reinstalar
    todo. Acá, en ssPostInstall, Python YA esta instalado, asi que la ruta
    resuelve y el acceso directo se reescribe correcto. }
  if CurStep = ssPostInstall then
  begin
    PyW := FindPythonW('');
    if (PyW <> '') and (Pos('\', PyW) > 0) and FileExists(PyW) then
    begin
      CreateShellLink(
        ExpandConstant('{commondesktop}\{#AppName}.lnk'),
        ExpandConstant('{#AppName} v{#AppVersion} — Gameplay Alliance'),
        PyW,
        ExpandConstant('"{app}\pleiada_app.pyw"'),
        ExpandConstant('{app}'),
        ExpandConstant('{app}\gameplay_recorder.ico'), 0, SW_SHOWNORMAL);
    end
    else
      { Sin ruta valida no se toca el acceso directo: mejor dejar el que haya
        que reemplazarlo por otro igual de roto. Queda el log del instalador. }
      Log('FindPythonW no resolvio una ruta valida: ' + PyW);
  end;
end;

#ifndef LITE
var
  ConsentPage:  TWizardPage;
  ConsentMemo:  TNewMemo;
  ConsentCheck: TNewCheckBox;
  ConsentLink:  TNewStaticText;

procedure InitializeWizard;
begin
  ConsentPage := CreateCustomPage(
    wpWelcome,
    'Bienvenido a Gameplay Recorder - Gameplay Alliance',
    'Leé atentamente la siguiente información antes de continuar.'
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
  ConsentMemo.Lines.Add('¡Bienvenidos al Gameplay Alliance!');
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    'Gameplay Recorder es la herramienta oficial del programa Gameplay Alliance. ' +
    'Está construida exclusivamente sobre bibliotecas de código ' +
    'abierto y es completamente segura de instalar y utilizar.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add('QUÉ INSTALA ESTE PROGRAMA:');
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    '- AutoHotkey v2 (https://www.autohotkey.com/)' + #13#10 +
    '  Software libre de código abierto que registra de forma anonimizada ' +
    'la actividad del teclado y del mouse durante la sesión de grabación.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    '- OBS Studio (https://obsproject.com/)' + #13#10 +
    '  Software libre de código abierto para grabar la pantalla durante el gameplay.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add('SOBRE LOS DATOS RECOPILADOS:');
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    'Toda la información recopilada por este software es y debe ser estrictamente ' +
    'anónima. No se almacena ni transmite ningún dato de identificación personal.'
  );
  ConsentMemo.Lines.Add('');
  ConsentMemo.Lines.Add(
    'Al continuar con la instalación, confirmás que has leído y firmado los ' +
    'términos y condiciones, que sos mayor de edad y que participás ' +
    'voluntariamente en el programa.'
  );

  // Bug 1: el texto + URL larga no entraba en una línea. Lo separamos en dos:
  //   checkbox con el texto (1 línea) + la URL en un label debajo.
  ConsentCheck := TNewCheckBox.Create(ConsentPage);
  ConsentCheck.Parent  := ConsentPage.Surface;
  ConsentCheck.Left    := 0;
  ConsentCheck.Top     := ConsentPage.SurfaceHeight - 40;
  ConsentCheck.Width   := ConsentPage.SurfaceWidth;
  ConsentCheck.Height  := 20;
  ConsentCheck.Caption := 'Acepto los términos y condiciones del programa.';

  ConsentLink := TNewStaticText.Create(ConsentPage);
  ConsentLink.Parent  := ConsentPage.Surface;
  ConsentLink.Left    := 20;
  ConsentLink.Top     := ConsentPage.SurfaceHeight - 18;
  ConsentLink.Width   := ConsentPage.SurfaceWidth - 20;
  ConsentLink.Caption := 'https://gameplayalliance.gg/terminos-condiciones';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ConsentPage.ID then
  begin
    if not ConsentCheck.Checked then
    begin
      MsgBox(
        'Debés marcar la casilla para confirmar que has leído los términos y condiciones antes de continuar.',
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
#endif

#ifndef LITE
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
#endif



































