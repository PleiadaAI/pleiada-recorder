#Requires AutoHotkey v2.0
#SingleInstance Force

; ══════════════════════════════════════════════════════
;  PLEIADA — Gameplay Logger V12
;  Ventana floating — UI v2.1
;
;  REQUISITO: obs_control.py debe estar en la misma
;  carpeta que este script.
; ══════════════════════════════════════════════════════

; ── Carpeta base de grabaciones ───────────────────────
global baseDir   := A_MyDocuments . "\Pleiada Recordings"
global logDir    := ""
global mouseFile := ""
global keyFile   := ""
global videoFile := ""

; ── Handles de archivo ────────────────────────────────
global mouseFH := 0
global keyFH   := 0
global videoFH := 0

; ── Estado ────────────────────────────────────────────
global recording       := false
global lastX           := 0
global lastY           := 0
global recSeconds      := 0
global MAX_REC_SECONDS := 3900   ; 1 h 5 min

; ── Timer de alta precision ───────────────────────────
global freqQPC   := 0
global startQPC  := 0
global startUnix := 0

; ── GUI handles ───────────────────────────────────────
global gMain             := 0
global btnIdle           := 0   ; boton estado idle (purple)
global btnRec            := 0   ; boton estado grabando (red)
global lblStatusDot      := 0
global lblStatus         := 0
global lblTimer          := 0
global lblCountdown      := 0
global lblCountdownLabel := 0
global lblSession        := 0

; ── Estado de sesion (para hipervínculo post-grabacion) ──
global sessionName      := ""
global lastLogDir       := ""
global sessionCompleted := false

; ════════════════════════════════════════════════════════
;  TIMER DE ALTA PRECISION
; ════════════════════════════════════════════════════════

InitTimer() {
    global freqQPC, startQPC, startUnix
    local fq := 0, sq := 0
    DllCall("QueryPerformanceFrequency", "Int64*", &fq)
    DllCall("QueryPerformanceCounter",   "Int64*", &sq)
    freqQPC  := fq
    startQPC := sq
    startUnix := DateDiff(A_NowUTC, "19700101000000", "Seconds") * 1000 + A_MSec
}

NowMs() {
    global freqQPC, startQPC, startUnix
    local count := 0
    DllCall("QueryPerformanceCounter", "Int64*", &count)
    return Round(startUnix + (count - startQPC) / freqQPC * 1000)
}

FormatCountdown(remaining) {
    if remaining < 0
        remaining := 0
    h := remaining // 3600
    m := (remaining - h * 3600) // 60
    s := Mod(remaining, 60)
    return Format("{:02d}:{:02d}:{:02d}", h, m, s)
}

; ════════════════════════════════════════════════════════
;  CONTROL DE OBS
; ════════════════════════════════════════════════════════

OBSStart() {
    script := A_ScriptDir . "\obs_control.py"
    return RunWait('pythonw "' . script . '" start', , "Hide")
}

OBSStop(sessionDir := "") {
    script := A_ScriptDir . "\obs_control.py"
    args   := sessionDir != "" ? ' stop "' . sessionDir . '"' : " stop"
    Run('pythonw "' . script . '"' . args, , "Hide")
}

; ════════════════════════════════════════════════════════
;  TRACKING
; ════════════════════════════════════════════════════════

TrackMouse() {
    global recording, mouseFH, lastX, lastY
    if !recording
        return
    MouseGetPos(&x, &y)
    if (x != lastX || y != lastY) {
        mouseFH.WriteLine(NowMs() . ",MOVE," . x . "," . y . ",")
        lastX := x
        lastY := y
    }
}

TrackTimeline() {
    global recording, videoFH
    if !recording
        return
    videoFH.WriteLine(NowMs() . ",FRAME")
}

LogKey(vk) {
    global recording, keyFH
    if !recording
        return
    keyName := GetKeyName(Format("vk{:02X}", vk))
    keyFH.WriteLine(NowMs() . ",KEY_DOWN," . keyName . "," . Format("{:02X}", vk))
}

; ════════════════════════════════════════════════════════
;  TICK (reloj UI — 1 segundo)
; ════════════════════════════════════════════════════════

TickTimer() {
    global recording, recSeconds, lblTimer, lblCountdown
    if !recording
        return
    recSeconds++
    h := recSeconds // 3600
    m := (recSeconds - h * 3600) // 60
    s := Mod(recSeconds, 60)
    lblTimer.Value := Format("{:02d}:{:02d}:{:02d}", h, m, s)
    remaining := MAX_REC_SECONDS - recSeconds
    lblCountdown.Value := FormatCountdown(remaining)
    if remaining <= 300
        lblCountdown.SetFont("s11 cFEBC2E bold", "Segoe UI")
    else
        lblCountdown.SetFont("s11 cE0E0E0", "Segoe UI Light")
    if recSeconds >= MAX_REC_SECONDS
        AutoStopRecording()
}

AutoStopRecording() {
    StopRecording()
    MsgBox(
        "La grabación se detuvo automáticamente al alcanzar el límite de 1h 5min.`n`nPodés iniciar una nueva grabación cuando quieras.",
        "Pleiada Recorder", "Icon! T10"
    )
}

; ════════════════════════════════════════════════════════
;  GRABAR / DETENER
; ════════════════════════════════════════════════════════

OnRecordBtn(*) {
    global recording
    if recording
        StopRecording()
    else
        StartRecording()
}

StartRecording() {
    global recording, mouseFH, keyFH, videoFH
    global mouseFile, keyFile, videoFile, logDir, baseDir
    global recSeconds, btnIdle, btnRec
    global lblStatusDot, lblStatus, lblTimer, lblCountdown, lblCountdownLabel, lblSession
    global sessionName, lastLogDir, sessionCompleted

    if recording
        return

    ; Crear carpeta de sesion con timestamp
    sessionName := FormatTime(, "yyyy-MM-dd HH-mm-ss")
    logDir      := baseDir . "\" . sessionName . " recording"
    sessionCompleted := false
    if !DirExist(baseDir)
        DirCreate(baseDir)
    DirCreate(logDir)
    mouseFile := logDir . "\mouse_log.csv"
    keyFile   := logDir . "\key_log.csv"
    videoFile := logDir . "\video_timeline.csv"

    ; UI: estado "iniciando"
    lblStatus.Value := "Iniciando..."
    btnIdle.Enabled := false

    ; Lanzar OBS y esperar confirmacion (RunWait bloquea hasta que Python termina)
    exitCode := OBSStart()
    if exitCode != 0 {
        lblStatus.Value := "Listo para grabar"
        btnIdle.Enabled := true
        MsgBox(
            "Error: OBS no pudo iniciar la grabación.`n`n"
            . "Revisá el log en:`n" . A_Temp . "\pleiada_obs_debug.txt",
            "Pleiada Recorder", "Icon! T10"
        )
        return
    }

    ; Abrir CSVs y escribir headers + anchor
    InitTimer()
    mouseFH := FileOpen(mouseFile, "w", "UTF-8")
    keyFH   := FileOpen(keyFile,   "w", "UTF-8")
    videoFH := FileOpen(videoFile, "w", "UTF-8")
    mouseFH.WriteLine("timestamp_ms,event_type,x,y,button")
    keyFH.WriteLine("timestamp_ms,event_type,key,vk_code")
    videoFH.WriteLine("timestamp_ms,event_type")
    anchorTs := NowMs()
    mouseFH.WriteLine(anchorTs . ",ANCHOR_START,,,")
    keyFH.WriteLine(anchorTs   . ",ANCHOR_START,,")
    videoFH.WriteLine(anchorTs . ",ANCHOR_START")

    ; Activar estado grabando
    recording  := true
    recSeconds := 0

    ; UI: estado grabando
    btnIdle.Visible := false
    btnRec.Visible  := true
    btnIdle.Enabled := true

    lblStatusDot.SetFont("s9 cE05555 bold", "Segoe UI")
    lblStatus.Value := "Grabando..."
    lblStatus.SetFont("s9 cE07575 norm", "Segoe UI")

    lblTimer.Value := "00:00:00"
    lblTimer.SetFont("s15 cE07575", "Segoe UI Light")

    lblCountdown.Value := FormatCountdown(MAX_REC_SECONDS)
    lblCountdown.SetFont("s11 cE0E0E0", "Segoe UI Light")
    lblCountdownLabel.Value := "Límite de sesión"
    lblCountdownLabel.SetFont("s7 cE05555 w700", "Segoe UI")

    lblSession.Value := sessionName . " recording"
    lblSession.SetFont("s8 cE05555 norm", "Segoe UI")
    sessionCompleted := false

    ; Iniciar timers
    SetTimer(TrackMouse,    8)
    SetTimer(TrackTimeline, 50)
    SetTimer(TickTimer,     1000)
}

StopRecording() {
    global recording, mouseFH, keyFH, videoFH, logDir
    global recSeconds, btnIdle, btnRec
    global lblStatusDot, lblStatus, lblTimer, lblCountdown, lblCountdownLabel, lblSession
    global sessionName, lastLogDir, sessionCompleted

    if !recording
        return

    ; Detener timers de tracking
    SetTimer(TrackMouse,    0)
    SetTimer(TrackTimeline, 0)
    SetTimer(TickTimer,     0)

    ; Escribir anchor final y cerrar archivos
    endTs := NowMs()
    mouseFH.WriteLine(endTs . ",ANCHOR_END,,,")
    keyFH.WriteLine(endTs   . ",ANCHOR_END,,")
    videoFH.WriteLine(endTs . ",ANCHOR_END")
    mouseFH.Close()
    keyFH.Close()
    videoFH.Close()
    recording := false

    ; Detener OBS en background (no bloquea AHK)
    OBSStop(logDir)

    ; UI: volver al estado idle
    btnRec.Visible  := false
    btnIdle.Visible := true

    lblStatusDot.SetFont("s9 c6B68C4 bold", "Segoe UI")
    lblStatus.Value := "Listo para grabar"
    lblStatus.SetFont("s9 c7b78a8 norm", "Segoe UI")

    lblTimer.Value := "00:00:00"
    lblTimer.SetFont("s15 cE0E0E0", "Segoe UI Light")

    lblCountdown.Value := "01:05:00"
    lblCountdown.SetFont("s11 cE0E0E0", "Segoe UI Light")
    lblCountdownLabel.Value := "Límite de sesión"
    lblCountdownLabel.SetFont("s7 c6B68C4 w700", "Segoe UI")

    ; Guardar carpeta y activar hipervínculo
    lastLogDir := logDir
    sessionCompleted := true
    lblSession.Value := sessionName . " recording"
    lblSession.SetFont("s8 c8888ee norm", "Segoe UI")
}

; ════════════════════════════════════════════════════════
;  CIERRE LIMPIO
; ════════════════════════════════════════════════════════

CloseFloater(*) {
    CloseAll()
    ExitApp()
}

CloseAll(*) {
    global recording, mouseFH, keyFH, videoFH, logDir
    if recording {
        SetTimer(TrackMouse,    0)
        SetTimer(TrackTimeline, 0)
        SetTimer(TickTimer,     0)
        endTs := NowMs()
        try mouseFH.WriteLine(endTs . ",ANCHOR_END,,,")
        try keyFH.WriteLine(endTs   . ",ANCHOR_END,,")
        try videoFH.WriteLine(endTs . ",ANCHOR_END")
        try mouseFH.Close()
        try keyFH.Close()
        try videoFH.Close()
        OBSStop(logDir)
        recording := false
    }
}

; ════════════════════════════════════════════════════════
;  HIPERVÍNCULO DE SESION
; ════════════════════════════════════════════════════════

OpenSessionFolder(*) {
    global sessionCompleted, lastLogDir
    if sessionCompleted && lastLogDir != ""
        Run('explorer "' . lastLogDir . '"')
}

; ════════════════════════════════════════════════════════
;  WM_NCHITTEST — arrastre por la zona del header
; ════════════════════════════════════════════════════════

WM_NCHITTEST_Handler(wParam, lParam, msg, hwnd) {
    global gMain
    if hwnd != gMain.Hwnd
        return
    sx := lParam & 0xFFFF
    if sx >= 0x8000
        sx -= 0x10000
    sy := (lParam >> 16) & 0xFFFF
    if sy >= 0x8000
        sy -= 0x10000
    pt := Buffer(8)
    NumPut("Int", sx, pt, 0)
    NumPut("Int", sy, pt, 4)
    DllCall("ScreenToClient", "Ptr", hwnd, "Ptr", pt)
    localY := NumGet(pt, 4, "Int")
    if localY < 34
        return 2
}

; ════════════════════════════════════════════════════════
;  CREAR VENTANA FLOATING
; ════════════════════════════════════════════════════════

CreateFloater() {
    global gMain, btnIdle, btnRec
    global lblStatusDot, lblStatus, lblTimer
    global lblCountdown, lblCountdownLabel, lblSession

    WIN_W := 300
    WIN_H := 182

    gMain := Gui("-Caption +ToolWindow +AlwaysOnTop")
    gMain.BackColor := "0d0d18"
    gMain.MarginX   := 0
    gMain.MarginY   := 0

    ; ════════════════════════════════════════
    ;  TITLE BAR (fondo oscuro 0a0a12)
    ; ════════════════════════════════════════

    ; Fondo de la barra de titulo
    gMain.Add("Text", "x0 y0 w300 h33 Background0a0a12", "")

    ; Acento superior (3px purple)
    gMain.Add("Text", "x0 y0 w300 h3 Background7c6fcd", "")

    ; Icono constelacion
    gMain.SetFont("s10 c6B68C4 bold", "Segoe UI")
    gMain.Add("Text", "x12 y10 w16 h14 Background0a0a12 Center", "✦")

    ; Nombre
    gMain.SetFont("s9 cDDDDDD w500", "Segoe UI")
    gMain.Add("Text", "x31 y12 w182 h12 Background0a0a12", "Pleiada Recorder")

    ; Dot rojo con X (cerrar) — alineado a la derecha
    gMain.SetFont("s6 cFFFFFF w700", "Segoe UI")
    btnDotClose := gMain.Add("Text", "x277 y11 w11 h11 BackgroundFF5F57 Center +0x200", "x")
    btnDotClose.OnEvent("Click", (*) => CloseFloater())

    ; Separador cabecera / cuerpo
    gMain.Add("Text", "x0 y33 w300 h1 Background2a2850", "")

    ; ════════════════════════════════════════
    ;  FILA DE ESTADO (y ≈ 40-62)
    ; ════════════════════════════════════════

    ; Dot de estado
    gMain.SetFont("s9 c6B68C4 bold", "Segoe UI")
    lblStatusDot := gMain.Add("Text", "x16 y43 w12 h12 BackgroundTrans", "●")

    ; Texto de estado
    gMain.SetFont("s9 c7b78a8 norm", "Segoe UI")
    lblStatus := gMain.Add("Text", "x32 y43 w130 h13 BackgroundTrans", "Listo para grabar")

    ; Timer (grande, ligero — Segoe UI Light = weight 300)
    gMain.SetFont("s15 cE0E0E0", "Segoe UI Light")
    lblTimer := gMain.Add("Text", "x160 y37 w128 h24 Right BackgroundTrans", "00:00:00")

    ; ════════════════════════════════════════
    ;  PILL DE COUNTDOWN (y=65-89)
    ; ════════════════════════════════════════

    ; Fondo de la pill (color ligeramente distinto al bg)
    ctrlPillBg := gMain.Add("Text", "x10 y75 w280 h26 Background141426", "")

    ; Etiqueta "Límite de sesión"
    gMain.SetFont("s7 c6B68C4 w700", "Segoe UI")
    lblCountdownLabel := gMain.Add("Text", "x18 y80 w148 h13 Background141426", "Límite de sesión")

    ; Valor del countdown — Segoe UI Light para consistencia tipografica
    gMain.SetFont("s11 cE0E0E0", "Segoe UI Light")
    lblCountdown := gMain.Add("Text", "x178 y76 w104 h18 Right Background141426", "01:05:00")

    ; Rounded corners en la pill (radio 8px)
    hRgnPill := DllCall("CreateRoundRectRgn", "Int", 0, "Int", 0, "Int", 280, "Int", 26, "Int", 16, "Int", 16, "Ptr")
    DllCall("SetWindowRgn", "Ptr", ctrlPillBg.Hwnd, "Ptr", hRgnPill, "Int", true)

    ; ════════════════════════════════════════
    ;  SEPARADOR
    ; ════════════════════════════════════════

    gMain.Add("Text", "x0 y106 w300 h1 Background2a2850", "")

    ; ════════════════════════════════════════
    ;  BOTON PRINCIPAL (Text control coloreado)
    ; ════════════════════════════════════════

    ; Estado idle — fondo morado
    gMain.SetFont("s10 cFFFFFF w500", "Segoe UI")
    btnIdle := gMain.Add("Text", "x10 y112 w280 h35 Background7d7ad0 Center +0x200", "Iniciar grabación")
    btnIdle.OnEvent("Click", OnRecordBtn)

    ; Estado grabando — fondo rojo oscuro (oculto al inicio)
    gMain.SetFont("s10 cE07575 w500", "Segoe UI")
    btnRec := gMain.Add("Text", "x10 y112 w280 h35 Background2a1010 Center +0x200 Hidden", "Detener grabación")
    btnRec.OnEvent("Click", OnRecordBtn)

    ; Rounded corners en ambos botones (radio 14px — mismo nivel que la ventana)
    hRgnIdle := DllCall("CreateRoundRectRgn", "Int", 0, "Int", 0, "Int", 280, "Int", 35, "Int", 28, "Int", 28, "Ptr")
    DllCall("SetWindowRgn", "Ptr", btnIdle.Hwnd, "Ptr", hRgnIdle, "Int", true)
    hRgnRec  := DllCall("CreateRoundRectRgn", "Int", 0, "Int", 0, "Int", 280, "Int", 35, "Int", 28, "Int", 28, "Ptr")
    DllCall("SetWindowRgn", "Ptr", btnRec.Hwnd,  "Ptr", hRgnRec,  "Int", true)

    ; ════════════════════════════════════════
    ;  FILA DE METADATOS DE SESION
    ; ════════════════════════════════════════

    gMain.SetFont("s7 c6B68C4 w700", "Segoe UI")
    gMain.Add("Text", "x16 y157 w50 h13 BackgroundTrans", "Sesión")

    gMain.SetFont("s8 ca0a0c0 norm", "Segoe UI")
    lblSession := gMain.Add("Text", "x75 y157 w214 h13 Right BackgroundTrans", "No iniciada")
    lblSession.OnEvent("Click", OpenSessionFolder)

    ; ════════════════════════════════════════
    ;  EVENTOS Y POSICION
    ; ════════════════════════════════════════

    OnMessage(0x84, WM_NCHITTEST_Handler)
    gMain.OnEvent("Close", CloseFloater)

    ; Centrado horizontalmente, pegado al borde inferior
    MonitorGetWorkArea(1, &waLeft, &waTop, &waRight, &waBottom)
    winX := waLeft + (waRight - waLeft - WIN_W) // 2
    winY := waBottom - WIN_H - 8

    gMain.Show("w" . WIN_W . " h" . WIN_H . " x" . winX . " y" . winY . " NoActivate")

    ; Rounded corners via DWM (Windows 11+)
    ; DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
    DllCall("dwmapi\DwmSetWindowAttribute",
        "Ptr",  gMain.Hwnd,
        "UInt", 33,
        "UInt*", 2,
        "UInt", 4)
}

; ════════════════════════════════════════════════════════
;  HOTKEYS DE TRACKING (mouse y teclado — sin bloquear input)
; ════════════════════════════════════════════════════════

~*LButton:: {
    global recording, mouseFH
    if !recording
        return
    MouseGetPos(&x, &y)
    mouseFH.WriteLine(NowMs() . ",CLICK," . x . "," . y . ",LEFT")
}

~*RButton:: {
    global recording, mouseFH
    if !recording
        return
    MouseGetPos(&x, &y)
    mouseFH.WriteLine(NowMs() . ",CLICK," . x . "," . y . ",RIGHT")
}

~*MButton:: {
    global recording, mouseFH
    if !recording
        return
    MouseGetPos(&x, &y)
    mouseFH.WriteLine(NowMs() . ",CLICK," . x . "," . y . ",MIDDLE")
}

; Letras
~*a:: LogKey(GetKeyVK("a"))
~*b:: LogKey(GetKeyVK("b"))
~*c:: LogKey(GetKeyVK("c"))
~*d:: LogKey(GetKeyVK("d"))
~*e:: LogKey(GetKeyVK("e"))
~*f:: LogKey(GetKeyVK("f"))
~*g:: LogKey(GetKeyVK("g"))
~*h:: LogKey(GetKeyVK("h"))
~*i:: LogKey(GetKeyVK("i"))
~*j:: LogKey(GetKeyVK("j"))
~*k:: LogKey(GetKeyVK("k"))
~*l:: LogKey(GetKeyVK("l"))
~*m:: LogKey(GetKeyVK("m"))
~*n:: LogKey(GetKeyVK("n"))
~*o:: LogKey(GetKeyVK("o"))
~*p:: LogKey(GetKeyVK("p"))
~*q:: LogKey(GetKeyVK("q"))
~*r:: LogKey(GetKeyVK("r"))
~*s:: LogKey(GetKeyVK("s"))
~*t:: LogKey(GetKeyVK("t"))
~*u:: LogKey(GetKeyVK("u"))
~*v:: LogKey(GetKeyVK("v"))
~*w:: LogKey(GetKeyVK("w"))
~*x:: LogKey(GetKeyVK("x"))
~*y:: LogKey(GetKeyVK("y"))
~*z:: LogKey(GetKeyVK("z"))
; Numeros
~*0:: LogKey(GetKeyVK("0"))
~*1:: LogKey(GetKeyVK("1"))
~*2:: LogKey(GetKeyVK("2"))
~*3:: LogKey(GetKeyVK("3"))
~*4:: LogKey(GetKeyVK("4"))
~*5:: LogKey(GetKeyVK("5"))
~*6:: LogKey(GetKeyVK("6"))
~*7:: LogKey(GetKeyVK("7"))
~*8:: LogKey(GetKeyVK("8"))
~*9:: LogKey(GetKeyVK("9"))
; Teclas especiales de juego
~*Space::  LogKey(GetKeyVK("Space"))
~*Enter::  LogKey(GetKeyVK("Enter"))
~*Shift::  LogKey(GetKeyVK("Shift"))
~*LShift:: LogKey(GetKeyVK("LShift"))
~*RShift:: LogKey(GetKeyVK("RShift"))
~*Ctrl::   LogKey(GetKeyVK("Ctrl"))
~*LCtrl::  LogKey(GetKeyVK("LCtrl"))
~*RCtrl::  LogKey(GetKeyVK("RCtrl"))
~*Alt::    LogKey(GetKeyVK("Alt"))
~*LAlt::   LogKey(GetKeyVK("LAlt"))
~*RAlt::   LogKey(GetKeyVK("RAlt"))
~*Tab::    LogKey(GetKeyVK("Tab"))
~*Escape:: LogKey(GetKeyVK("Escape"))
~*Up::     LogKey(GetKeyVK("Up"))
~*Down::   LogKey(GetKeyVK("Down"))
~*Left::   LogKey(GetKeyVK("Left"))
~*Right::  LogKey(GetKeyVK("Right"))
~*F1::     LogKey(GetKeyVK("F1"))
~*F2::     LogKey(GetKeyVK("F2"))
~*F3::     LogKey(GetKeyVK("F3"))
~*F4::     LogKey(GetKeyVK("F4"))
~*F5::     LogKey(GetKeyVK("F5"))
~*F6::     LogKey(GetKeyVK("F6"))
~*F7::     LogKey(GetKeyVK("F7"))
~*F8::     LogKey(GetKeyVK("F8"))
; F9 y F10 no se loggean (eran de control en versiones anteriores)

; ════════════════════════════════════════════════════════
;  INICIO
; ════════════════════════════════════════════════════════

OnExit(CloseAll)
Persistent()
CreateFloater()
