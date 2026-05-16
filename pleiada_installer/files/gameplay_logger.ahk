#Requires AutoHotkey v2.0
#SingleInstance Force

; ══════════════════════════════════════════════════════
;  PLEIADA — Gameplay Logger V14
;  Ventana floating — UI v2.2
;
;  CAMBIOS V14 (Bug 4 — overlay no invasivo):
;  · Ventana visible en la taskbar de Windows → Alt+Tab para traerla
;    al frente sin interrumpir el juego.
;  · Eliminado +AlwaysOnTop: el floater ya no queda superpuesto al
;    juego y tampoco queda grabado en el video.
;  · El Raw Input (RIDEV_INPUTSINK) sigue capturando teclado y mouse
;    aunque el juego tenga el foco — no se pierde ningún evento.
;
;  CAMBIOS V13 (Raw Input refactor — Issues 1/2/3):
;  · mouse_delta_log.csv NUEVO: dx/dy por evento de hardware,
;    funciona aunque el juego tenga el cursor bloqueado
;  · key_log: KEY_UP + KEY_DOWN, sin auto-repeat, TODAS las teclas
;    (reemplaza whitelist de ~60 hotkeys por WM_INPUT keyboard)
;  · mouse_log: botones via Raw Input (BUTTON_DOWN/UP en vez de CLICK),
;    agrega X1/X2 y scroll wheel; cursor-position timer se mantiene
;  · Un solo RegisterRawInputDevices cubre mouse + teclado
;
;  REQUISITO: obs_control.py debe estar en la misma carpeta.
; ══════════════════════════════════════════════════════

; ── Carpeta base de grabaciones ───────────────────────
global baseDir   := A_MyDocuments . "\Pleiada Recordings"
global logDir    := ""
global mouseFile := ""
global deltaFile := ""   ; mouse_delta_log.csv (Raw Input deltas)
global keyFile   := ""
global videoFile := ""

; ── Handles de archivo ────────────────────────────────
global mouseFH := 0
global deltaFH := 0
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
global btnIdle           := 0
global btnRec            := 0
global lblStatusDot      := 0
global lblStatus         := 0
global lblTimer          := 0
global lblCountdown      := 0
global lblCountdownLabel := 0
global lblSession        := 0

; ── Estado de sesion ──────────────────────────────────
global sessionName      := ""
global lastLogDir       := ""
global sessionCompleted := false

; ── Seguimiento de teclas presionadas (filtro auto-repeat) ──
global pressedKeys := Map()

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
;  RAW INPUT — registro y handler
;
;  Se registran mouse (UsagePage=1, Usage=2) y teclado
;  (UsagePage=1, Usage=6) con RIDEV_INPUTSINK (0x100) para
;  recibir eventos aunque el juego tenga el foco.
;
;  Mouse  → mouse_delta_log.csv (dx/dy) + mouse_log.csv (botones)
;  Teclado → key_log.csv (KEY_DOWN / KEY_UP, sin auto-repeat)
;
;  Struct sizes (x64):
;    RAWINPUTDEVICE : usUsagePage(2)+usUsage(2)+dwFlags(4)+hwnd(8) = 16 bytes
;    RAWINPUTHEADER : dwType(4)+dwSize(4)+hDevice(8)+wParam(8)     = 24 bytes
;    RAWMOUSE data  : usFlags(2)+[pad2]+ulButtons(4)+ulRaw(4)+lX(4)+lY(4)+extra(4) = 24 bytes
;    RAWKEYBOARD    : MakeCode(2)+Flags(2)+Rsvd(2)+VKey(2)+Msg(4)+Extra(4) = 16 bytes
;
;  Offsets en el buffer RAWINPUT (header en 0..23, data desde 24):
;    RAWMOUSE.usFlags       = 24
;    RAWMOUSE.usButtonFlags = 28  (dentro de la union a +4)
;    RAWMOUSE.usButtonData  = 30  (+6, scroll delta)
;    RAWMOUSE.lLastX        = 36  (+12)
;    RAWMOUSE.lLastY        = 40  (+16)
;    RAWKEYBOARD.Flags      = 26  (+2, bit 0 = RI_KEY_BREAK)
;    RAWKEYBOARD.VKey       = 30  (+6)
; ════════════════════════════════════════════════════════

RegisterRawInput() {
    ; Registra mouse + teclado en una sola llamada
    cbRid    := 16           ; sizeof(RAWINPUTDEVICE) en x64
    nDevices := 2
    rid      := Buffer(cbRid * nDevices, 0)

    ; Entrada 0 — Mouse (UsagePage=1, Usage=2)
    NumPut("UShort", 1,     rid,  0)   ; usUsagePage
    NumPut("UShort", 2,     rid,  2)   ; usUsage
    NumPut("UInt",   0x100, rid,  4)   ; dwFlags = RIDEV_INPUTSINK
    NumPut("Ptr", A_ScriptHwnd, rid, 8)   ; hwndTarget

    ; Entrada 1 — Teclado (UsagePage=1, Usage=6)
    NumPut("UShort", 1,     rid, 16)
    NumPut("UShort", 6,     rid, 18)
    NumPut("UInt",   0x100, rid, 20)
    NumPut("Ptr", A_ScriptHwnd, rid, 24)

    ok := DllCall("RegisterRawInputDevices", "Ptr", rid, "UInt", nDevices, "UInt", cbRid)
    return ok
}

HandleRawInput(wParam, lParam, msg, hwnd) {
    global recording, mouseFH, deltaFH, keyFH, pressedKeys

    if !recording
        return

    ; ── Obtener tamaño del buffer necesario ───────────
    cbSize := 0
    DllCall("GetRawInputData",
        "Ptr",   lParam,
        "UInt",  0x10000003,   ; RID_INPUT
        "Ptr",   0,
        "UInt*", &cbSize,
        "UInt",  24)           ; sizeof(RAWINPUTHEADER) en x64

    if cbSize == 0
        return

    buf := Buffer(cbSize, 0)
    if DllCall("GetRawInputData",
            "Ptr",   lParam,
            "UInt",  0x10000003,
            "Ptr",   buf,
            "UInt*", &cbSize,
            "UInt",  24) == 0
        return

    dwType := NumGet(buf, 0, "UInt")
    ts     := NowMs()

    ; ── MOUSE (dwType == 0) ───────────────────────────
    if dwType == 0 {
        usFlags       := NumGet(buf, 24, "UShort")
        usButtonFlags := NumGet(buf, 28, "UShort")
        usButtonData  := NumGet(buf, 30, "UShort")   ; scroll delta (unsigned)
        lLastX        := NumGet(buf, 36, "Int")
        lLastY        := NumGet(buf, 40, "Int")

        ; Movimiento relativo → mouse_delta_log.csv
        ; usFlags & 0x01 == MOUSE_MOVE_ABSOLUTE: ignorar (tabletas, etc.)
        if (lLastX != 0 || lLastY != 0) && !(usFlags & 0x01)
            deltaFH.WriteLine(ts . ",MOVE," . lLastX . "," . lLastY)

        ; Eventos de botones → mouse_log.csv
        if usButtonFlags {
            MouseGetPos(&cx, &cy)

            if usButtonFlags & 0x0001
                mouseFH.WriteLine(ts . ",BUTTON_DOWN," . cx . "," . cy . ",LEFT")
            if usButtonFlags & 0x0002
                mouseFH.WriteLine(ts . ",BUTTON_UP,"   . cx . "," . cy . ",LEFT")
            if usButtonFlags & 0x0004
                mouseFH.WriteLine(ts . ",BUTTON_DOWN," . cx . "," . cy . ",RIGHT")
            if usButtonFlags & 0x0008
                mouseFH.WriteLine(ts . ",BUTTON_UP,"   . cx . "," . cy . ",RIGHT")
            if usButtonFlags & 0x0010
                mouseFH.WriteLine(ts . ",BUTTON_DOWN," . cx . "," . cy . ",MIDDLE")
            if usButtonFlags & 0x0020
                mouseFH.WriteLine(ts . ",BUTTON_UP,"   . cx . "," . cy . ",MIDDLE")
            if usButtonFlags & 0x0040
                mouseFH.WriteLine(ts . ",BUTTON_DOWN," . cx . "," . cy . ",X1")
            if usButtonFlags & 0x0080
                mouseFH.WriteLine(ts . ",BUTTON_UP,"   . cx . "," . cy . ",X1")
            if usButtonFlags & 0x0100
                mouseFH.WriteLine(ts . ",BUTTON_DOWN," . cx . "," . cy . ",X2")
            if usButtonFlags & 0x0200
                mouseFH.WriteLine(ts . ",BUTTON_UP,"   . cx . "," . cy . ",X2")

            ; Scroll: usButtonData es un SHORT con signo (120 = un tick arriba)
            if usButtonFlags & 0x0400 {
                delta := usButtonData
                if delta >= 0x8000   ; interpretar como signed short
                    delta -= 0x10000
                mouseFH.WriteLine(ts . ",SCROLL," . cx . "," . cy . "," . delta)
            }
            ; Scroll horizontal (usButtonFlags & 0x0800) — omitido por ahora
        }

    ; ── TECLADO (dwType == 1) ─────────────────────────
    } else if dwType == 1 {
        flags := NumGet(buf, 26, "UShort")   ; Flags: bit0 = RI_KEY_BREAK
        vKey  := NumGet(buf, 30, "UShort")   ; VKey

        ; Ignorar códigos inválidos
        if vKey == 0 || vKey == 0xFF
            return

        isBreak := flags & 0x01   ; 1 = KEY_UP, 0 = KEY_DOWN

        if isBreak {
            ; KEY_UP — solo si teníamos registrado el KEY_DOWN
            if pressedKeys.Has(vKey) {
                pressedKeys.Delete(vKey)
                keyName := GetKeyName(Format("vk{:02X}", vKey))
                keyFH.WriteLine(ts . ",KEY_UP," . keyName . "," . Format("{:02X}", vKey))
            }
        } else {
            ; KEY_DOWN — ignorar auto-repeat (tecla ya estaba presionada)
            if !pressedKeys.Has(vKey) {
                pressedKeys[vKey] := true
                keyName := GetKeyName(Format("vk{:02X}", vKey))
                keyFH.WriteLine(ts . ",KEY_DOWN," . keyName . "," . Format("{:02X}", vKey))
            }
        }
    }
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
    global recording, mouseFH, deltaFH, keyFH, videoFH
    global mouseFile, deltaFile, keyFile, videoFile, logDir, baseDir
    global recSeconds, btnIdle, btnRec
    global lblStatusDot, lblStatus, lblTimer, lblCountdown, lblCountdownLabel, lblSession
    global sessionName, lastLogDir, sessionCompleted, pressedKeys

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
    deltaFile := logDir . "\mouse_delta_log.csv"
    keyFile   := logDir . "\key_log.csv"
    videoFile := logDir . "\video_timeline.csv"

    ; Limpiar estado de teclas presionadas
    pressedKeys := Map()

    ; UI: estado "iniciando"
    lblStatus.Value := "Iniciando..."
    btnIdle.Enabled := false

    ; Lanzar OBS y esperar confirmacion
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

    ; Abrir CSVs y escribir headers
    InitTimer()
    mouseFH := FileOpen(mouseFile, "w", "UTF-8")
    deltaFH := FileOpen(deltaFile, "w", "UTF-8")
    keyFH   := FileOpen(keyFile,   "w", "UTF-8")
    videoFH := FileOpen(videoFile, "w", "UTF-8")
    mouseFH.WriteLine("timestamp_ms,event_type,x,y,button")
    deltaFH.WriteLine("timestamp_ms,event_type,dx,dy")
    keyFH.WriteLine("timestamp_ms,event_type,key,vk_code")
    videoFH.WriteLine("timestamp_ms,event_type")

    ; Leer anchor timestamp calculado por obs_control.py
    anchorTs   := 0
    anchorFile := A_Temp . "\pleiada_anchor_ts.txt"
    if FileExist(anchorFile) {
        try {
            anchorContent := FileRead(anchorFile)
            anchorTs := Integer(Trim(anchorContent))
        }
        try FileDelete anchorFile
    }
    if anchorTs == 0
        anchorTs := NowMs()

    mouseFH.WriteLine(anchorTs . ",ANCHOR_START,,,")
    deltaFH.WriteLine(anchorTs . ",ANCHOR_START,,")
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
    global recording, mouseFH, deltaFH, keyFH, videoFH, logDir
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
    deltaFH.WriteLine(endTs . ",ANCHOR_END,,")
    keyFH.WriteLine(endTs   . ",ANCHOR_END,,")
    videoFH.WriteLine(endTs . ",ANCHOR_END")
    mouseFH.Close()
    deltaFH.Close()
    keyFH.Close()
    videoFH.Close()
    recording := false

    ; Detener OBS en background
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
    global recording, mouseFH, deltaFH, keyFH, videoFH, logDir
    if recording {
        SetTimer(TrackMouse,    0)
        SetTimer(TrackTimeline, 0)
        SetTimer(TickTimer,     0)
        endTs := NowMs()
        try mouseFH.WriteLine(endTs . ",ANCHOR_END,,,")
        try deltaFH.WriteLine(endTs . ",ANCHOR_END,,")
        try keyFH.WriteLine(endTs   . ",ANCHOR_END,,")
        try videoFH.WriteLine(endTs . ",ANCHOR_END")
        try mouseFH.Close()
        try deltaFH.Close()
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

    ; Sin +ToolWindow → aparece en taskbar de Windows (Alt+Tab).
    ; Sin +AlwaysOnTop → no queda superpuesto al juego ni grabado.
    ; El título "Pleiada Recorder" se muestra en la barra de tareas.
    gMain := Gui("-Caption", "Pleiada Recorder")
    gMain.BackColor := "0d0d18"
    gMain.MarginX   := 0
    gMain.MarginY   := 0

    ; ════════════════════════════════════════
    ;  TITLE BAR
    ; ════════════════════════════════════════

    gMain.Add("Text", "x0 y0 w300 h33 Background0a0a12", "")
    gMain.Add("Text", "x0 y0 w300 h3 Background7c6fcd", "")

    gMain.SetFont("s10 c6B68C4 bold", "Segoe UI")
    gMain.Add("Text", "x12 y10 w16 h14 Background0a0a12 Center", "✦")

    gMain.SetFont("s9 cDDDDDD w500", "Segoe UI")
    gMain.Add("Text", "x31 y12 w182 h12 Background0a0a12", "Pleiada Recorder")

    gMain.SetFont("s6 cFFFFFF w700", "Segoe UI")
    btnDotClose := gMain.Add("Text", "x277 y11 w11 h11 BackgroundFF5F57 Center +0x200", "x")
    btnDotClose.OnEvent("Click", (*) => CloseFloater())

    gMain.Add("Text", "x0 y33 w300 h1 Background2a2850", "")

    ; ════════════════════════════════════════
    ;  FILA DE ESTADO
    ; ════════════════════════════════════════

    gMain.SetFont("s9 c6B68C4 bold", "Segoe UI")
    lblStatusDot := gMain.Add("Text", "x16 y43 w12 h12 BackgroundTrans", "●")

    gMain.SetFont("s9 c7b78a8 norm", "Segoe UI")
    lblStatus := gMain.Add("Text", "x32 y43 w130 h13 BackgroundTrans", "Listo para grabar")

    gMain.SetFont("s15 cE0E0E0", "Segoe UI Light")
    lblTimer := gMain.Add("Text", "x160 y37 w128 h24 Right BackgroundTrans", "00:00:00")

    ; ════════════════════════════════════════
    ;  PILL DE COUNTDOWN
    ; ════════════════════════════════════════

    ctrlPillBg := gMain.Add("Text", "x10 y75 w280 h26 Background141426", "")

    gMain.SetFont("s7 c6B68C4 w700", "Segoe UI")
    lblCountdownLabel := gMain.Add("Text", "x18 y80 w148 h13 Background141426", "Límite de sesión")

    gMain.SetFont("s11 cE0E0E0", "Segoe UI Light")
    lblCountdown := gMain.Add("Text", "x178 y76 w104 h18 Right Background141426", "01:05:00")

    hRgnPill := DllCall("CreateRoundRectRgn", "Int", 0, "Int", 0, "Int", 280, "Int", 26, "Int", 16, "Int", 16, "Ptr")
    DllCall("SetWindowRgn", "Ptr", ctrlPillBg.Hwnd, "Ptr", hRgnPill, "Int", true)

    ; ════════════════════════════════════════
    ;  SEPARADOR
    ; ════════════════════════════════════════

    gMain.Add("Text", "x0 y106 w300 h1 Background2a2850", "")

    ; ════════════════════════════════════════
    ;  BOTON PRINCIPAL
    ; ════════════════════════════════════════

    gMain.SetFont("s10 cFFFFFF w500", "Segoe UI")
    btnIdle := gMain.Add("Text", "x10 y112 w280 h35 Background7d7ad0 Center +0x200", "Iniciar grabación")
    btnIdle.OnEvent("Click", OnRecordBtn)

    gMain.SetFont("s10 cE07575 w500", "Segoe UI")
    btnRec := gMain.Add("Text", "x10 y112 w280 h35 Background2a1010 Center +0x200 Hidden", "Detener grabación")
    btnRec.OnEvent("Click", OnRecordBtn)

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

    OnMessage(0x84,   WM_NCHITTEST_Handler)
    OnMessage(0x00FF, HandleRawInput)       ; WM_INPUT
    gMain.OnEvent("Close", CloseFloater)

    MonitorGetWorkArea(1, &waLeft, &waTop, &waRight, &waBottom)
    winX := waLeft + (waRight - waLeft - WIN_W) // 2
    winY := waBottom - WIN_H - 8

    gMain.Show("w" . WIN_W . " h" . WIN_H . " x" . winX . " y" . winY . " NoActivate")

    ; Ícono en taskbar y Alt+Tab (WM_SETICON)
    icoPath := A_ScriptDir . "\pleiada.ico"
    if FileExist(icoPath) {
        hIcon := LoadPicture(icoPath, "Icon1", &_t)
        SendMessage(0x0080, 0, hIcon, , gMain)   ; ICON_SMALL → taskbar
        SendMessage(0x0080, 1, hIcon, , gMain)   ; ICON_BIG   → Alt+Tab
    }

    DllCall("dwmapi\DwmSetWindowAttribute",
        "Ptr",  gMain.Hwnd,
        "UInt", 33,
        "UInt*", 2,
        "UInt", 4)
}

; ════════════════════════════════════════════════════════
;  INICIO
; ════════════════════════════════════════════════════════

OnExit(CloseAll)
Persistent()
CreateFloater()
RegisterRawInput()
