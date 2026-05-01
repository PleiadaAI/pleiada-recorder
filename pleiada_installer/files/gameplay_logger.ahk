#Requires AutoHotkey v2.0
#SingleInstance Force

; ══════════════════════════════════════════════════════
;  PLEIADA — Gameplay Logger V11
;  Ventana floating draggable — grabar / detener
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
global lastX          := 0
global lastY          := 0
global recSeconds     := 0
global MAX_REC_SECONDS := 3900   ; 1 h 5 min

; ── Timer de alta precision ───────────────────────────
global freqQPC   := 0
global startQPC  := 0
global startUnix := 0

; ── GUI handles ───────────────────────────────────────
global gMain     := 0
global btnRecord := 0
global lblAction := 0
global lblTimer  := 0

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
    global recording, recSeconds, lblTimer
    if !recording
        return
    recSeconds++
    h := recSeconds // 3600
    m := (recSeconds - h * 3600) // 60
    s := Mod(recSeconds, 60)
    lblTimer.Value := Format("{:02d}:{:02d}:{:02d}", h, m, s)
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
    global recSeconds, btnRecord, lblAction, lblTimer

    if recording
        return

    ; Crear carpeta de sesion con timestamp
    sessionName := FormatTime(, "yyyy-MM-dd HH-mm-ss")
    logDir      := baseDir . "\" . sessionName . " recording"
    if !DirExist(baseDir)
        DirCreate(baseDir)
    DirCreate(logDir)
    mouseFile := logDir . "\mouse_log.csv"
    keyFile   := logDir . "\key_log.csv"
    videoFile := logDir . "\video_timeline.csv"

    ; UI: estado "iniciando"
    lblAction.Value := "Iniciando..."
    btnRecord.Enabled := false

    ; Lanzar OBS y esperar confirmacion (RunWait bloquea hasta que Python termina)
    exitCode := OBSStart()
    if exitCode != 0 {
        lblAction.Value := "Iniciar grabación"
        btnRecord.Enabled := true
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

    ; UI: cambiar a icono/etiqueta de detener
    btnRecord.Enabled := true
    btnRecord.SetFont("s18 cFFFFFF", "Segoe UI Symbol")
    btnRecord.Text := "⏹"
    lblAction.Value := "Detener grabación"
    lblTimer.Value  := "00:00:00"

    ; Iniciar timers
    SetTimer(TrackMouse,    8)
    SetTimer(TrackTimeline, 50)
    SetTimer(TickTimer,     1000)
}

StopRecording() {
    global recording, mouseFH, keyFH, videoFH, logDir
    global recSeconds, btnRecord, lblAction, lblTimer

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
    btnRecord.SetFont("s18 cE53935", "Segoe UI Symbol")
    btnRecord.Text := "⏺"
    lblAction.Value := "Iniciar grabación"
    ; Timer se queda mostrando el tiempo final hasta nueva sesion
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
;  WM_NCHITTEST — arrastre por la zona del header
; ════════════════════════════════════════════════════════

WM_NCHITTEST_Handler(wParam, lParam, msg, hwnd) {
    global gMain
    if hwnd != gMain.Hwnd
        return
    ; Coordenadas de pantalla con signo (soporte multi-monitor)
    sx := lParam & 0xFFFF
    if sx >= 0x8000
        sx -= 0x10000
    sy := (lParam >> 16) & 0xFFFF
    if sy >= 0x8000
        sy -= 0x10000
    ; Convertir a coordenadas de cliente
    pt := Buffer(8)
    NumPut("Int", sx, pt, 0)
    NumPut("Int", sy, pt, 4)
    DllCall("ScreenToClient", "Ptr", hwnd, "Ptr", pt)
    localY := NumGet(pt, 4, "Int")
    ; Header hasta y=27: HTCAPTION (2) permite arrastrar la ventana
    if localY < 28
        return 2
}

; ════════════════════════════════════════════════════════
;  CREAR VENTANA FLOATING
; ════════════════════════════════════════════════════════

CreateFloater() {
    global gMain, btnRecord, lblAction, lblTimer

    gMain := Gui("-Caption +ToolWindow +AlwaysOnTop")
    gMain.BackColor := "1a1a2e"
    gMain.MarginX   := 0
    gMain.MarginY   := 0

    ; Barra de acento superior (3px violeta)
    gMain.Add("Text", "x0 y0 w300 h3 Background7c6fcd", "")

    ; Icono de punto (decorativo) + nombre en header
    gMain.SetFont("s9 c7c6fcd bold", "Segoe UI")
    gMain.Add("Text", "x10 y7 w14 h18 BackgroundTrans", "●")
    gMain.SetFont("s9 cE0E0E0 bold", "Segoe UI")
    gMain.Add("Text", "x26 y7 w190 h18 BackgroundTrans", "Pleiada Recorder")

    ; Boton cerrar (✕)
    gMain.SetFont("s8 c888888 norm", "Segoe UI")
    btnClose := gMain.Add("Button", "x268 y5 w24 h18", "✕")
    btnClose.OnEvent("Click", (*) => CloseFloater())

    ; Linea separadora header / cuerpo
    gMain.Add("Text", "x0 y27 w300 h1 Background2a2a4e", "")

    ; Boton grabar (icono grande — rojo en estado idle)
    gMain.SetFont("s18 cE53935", "Segoe UI Symbol")
    btnRecord := gMain.Add("Button", "x10 y33 w36 h36", "⏺")
    btnRecord.OnEvent("Click", OnRecordBtn)

    ; Etiqueta de accion
    gMain.SetFont("s9 cE0E0E0 norm", "Segoe UI")
    lblAction := gMain.Add("Text", "x54 y43 w140 h20 BackgroundTrans", "Iniciar grabación")

    ; Contador hh:mm:ss
    gMain.SetFont("s11 cE0E0E0 bold", "Consolas")
    lblTimer := gMain.Add("Text", "x194 y39 w96 h26 Right BackgroundTrans", "00:00:00")

    ; Registrar handler de arrastre por header
    OnMessage(0x84, WM_NCHITTEST_Handler)

    ; Evento de cierre (X del sistema operativo — aunque la ventana no tiene caption)
    gMain.OnEvent("Close", CloseFloater)

    ; Posicion: centrado horizontalmente, pegado al borde inferior del area de trabajo
    ; (por debajo del juego, para no aparecer en la grabacion)
    MonitorGetWorkArea(1, &waLeft, &waTop, &waRight, &waBottom)
    winW := 300
    winH := 78
    winX := waLeft + (waRight - waLeft - winW) // 2
    winY := waBottom - winH - 8   ; 8px sobre el borde inferior (encima de la barra de tareas)

    ; Mostrar sin robar el foco
    gMain.Show("w" . winW . " h" . winH . " x" . winX . " y" . winY . " NoActivate")
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
