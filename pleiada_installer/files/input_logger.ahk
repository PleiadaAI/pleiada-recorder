#Requires AutoHotkey v2.0
#SingleInstance Off

; ══════════════════════════════════════════════════════════════════
;  PLEIADA — Input Logger V1 (headless)
;  Uso: AutoHotkey64.exe input_logger.ahk "<logDir>"
;
;  Registra teclado y mouse via Raw Input (WM_INPUT).
;  El directorio de sesión se recibe como A_Args[1].
;  Lee el anchor timestamp de pleiada_anchor_ts.txt (escrito por
;  pleiada_app.pyw antes de lanzar este script).
;  Corre en background hasta que el proceso padre lo mata.
; ══════════════════════════════════════════════════════════════════

; ── Directorio de sesión ──────────────────────────────────────────
global logDir := A_Args.Length > 0 ? A_Args[1] : ""

if logDir = "" {
    ExitApp()
}

; ── PLE-43/13: exe del juego para filtrar inputs por ventana activa ──────────
; Si se recibe como segundo argumento, solo se loggea cuando ese proceso está en foco.
; Si está vacío, se loggea todo (comportamiento anterior — sin restricción).
global gameExe := A_Args.Length > 1 ? A_Args[2] : ""

; ── Archivos de log ───────────────────────────────────────────────
global mouseFile := logDir . "\mouse_log.csv"
global deltaFile := logDir . "\mouse_delta_log.csv"
global keyFile   := logDir . "\key_log.csv"
global videoFile := logDir . "\video_timeline.csv"
global stopFile  := logDir . "\pleiada_stop.txt"

; ── Handles de archivo ────────────────────────────────────────────
global mouseFH := 0
global deltaFH := 0
global keyFH   := 0
global videoFH := 0

; ── Estado ────────────────────────────────────────────────────────
global lastX      := 0
global lastY      := 0
global pressedKeys := Map()

; ── PLE-25: mapa de nombres para teclas OEM que GetKeyName retorna vacío ──────
; Cubre los caracteres de puntuación más comunes en teclado US-QWERTY.
global VK_FALLBACK := Map(
    0xBA, "Semicolon",   ; VK_OEM_1   → ;
    0xBB, "Equal",       ; VK_OEM_PLUS  → =
    0xBC, "Comma",       ; VK_OEM_COMMA → ,
    0xBD, "Minus",       ; VK_OEM_MINUS → -
    0xBE, "Period",      ; VK_OEM_PERIOD → .
    0xBF, "Slash",       ; VK_OEM_2   → /
    0xC0, "Backtick",    ; VK_OEM_3   → `
    0xDB, "LBracket",    ; VK_OEM_4   → [
    0xDC, "Backslash",   ; VK_OEM_5   → \
    0xDD, "RBracket",    ; VK_OEM_6   → ]
    0xDE, "Apostrophe",  ; VK_OEM_7   → '
)

; ── Timer de alta precision ───────────────────────────────────────
global freqQPC   := 0
global startQPC  := 0
global startUnix := 0

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

; ═══════════════════════════════════════════════════════════════════
;  RAW INPUT — registro y handler
;  (Igual que gameplay_logger.ahk V16 — sin cambios en la lógica)
;
;  Struct sizes (x64):
;    RAWINPUTDEVICE : 16 bytes por entrada
;    RAWINPUTHEADER : 24 bytes
;    Offsets en RAWINPUT data (desde byte 24):
;      RAWMOUSE.usFlags       = 24
;      RAWMOUSE.usButtonFlags = 28
;      RAWMOUSE.usButtonData  = 30
;      RAWMOUSE.lLastX        = 36
;      RAWMOUSE.lLastY        = 40
;      RAWKEYBOARD.Flags      = 26
;      RAWKEYBOARD.VKey       = 30
; ═══════════════════════════════════════════════════════════════════

RegisterRawInput() {
    cbRid    := 16
    nDevices := 2
    rid      := Buffer(cbRid * nDevices, 0)

    NumPut("UShort", 1,     rid,  0)
    NumPut("UShort", 2,     rid,  2)
    NumPut("UInt",   0x100, rid,  4)   ; RIDEV_INPUTSINK
    NumPut("Ptr", A_ScriptHwnd, rid, 8)

    NumPut("UShort", 1,     rid, 16)
    NumPut("UShort", 6,     rid, 18)
    NumPut("UInt",   0x100, rid, 20)
    NumPut("Ptr", A_ScriptHwnd, rid, 24)

    DllCall("RegisterRawInputDevices", "Ptr", rid, "UInt", nDevices, "UInt", cbRid)
}

HandleRawInput(wParam, lParam, msg, hwnd) {
    global mouseFH, deltaFH, keyFH, pressedKeys, gameExe

    ; PLE-43/13: no registrar inputs cuando el juego no está en primer plano.
    ; RIDEV_INPUTSINK captura input global; este filtro lo restringe al contexto del juego.
    if gameExe != "" && !WinActive("ahk_exe " . gameExe)
        return

    cbSize := 0
    DllCall("GetRawInputData",
        "Ptr",   lParam,
        "UInt",  0x10000003,
        "Ptr",   0,
        "UInt*", &cbSize,
        "UInt",  24)

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

    ; ── MOUSE (dwType == 0) ───────────────────────────────────────
    if dwType == 0 {
        usFlags       := NumGet(buf, 24, "UShort")
        usButtonFlags := NumGet(buf, 28, "UShort")
        usButtonData  := NumGet(buf, 30, "UShort")
        lLastX        := NumGet(buf, 36, "Int")
        lLastY        := NumGet(buf, 40, "Int")

        ; Movimiento relativo → mouse_delta_log.csv
        if (lLastX != 0 || lLastY != 0) && !(usFlags & 0x01)
            deltaFH.WriteLine(ts . ",MOVE," . lLastX . "," . lLastY)

        ; Botones → mouse_log.csv
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

            if usButtonFlags & 0x0400 {
                delta := usButtonData
                if delta >= 0x8000
                    delta -= 0x10000
                mouseFH.WriteLine(ts . ",SCROLL," . cx . "," . cy . "," . delta)
            }
        }

    ; ── TECLADO (dwType == 1) ─────────────────────────────────────
    } else if dwType == 1 {
        flags := NumGet(buf, 26, "UShort")
        vKey  := NumGet(buf, 30, "UShort")

        if vKey == 0 || vKey == 0xFF
            return

        isBreak := flags & 0x01

        if isBreak {
            if pressedKeys.Has(vKey) {
                pressedKeys.Delete(vKey)
                keyName := GetKeyName(Format("vk{:02X}", vKey))
                ; PLE-25: fallback para teclas OEM donde GetKeyName retorna vacío
                if keyName = ""
                    keyName := VK_FALLBACK.Has(vKey) ? VK_FALLBACK[vKey] : Format("vk{:02X}", vKey)
                keyFH.WriteLine(ts . ",KEY_UP," . keyName . "," . Format("{:02X}", vKey))
            }
        } else {
            if !pressedKeys.Has(vKey) {
                pressedKeys[vKey] := true
                keyName := GetKeyName(Format("vk{:02X}", vKey))
                ; PLE-25: fallback para teclas OEM donde GetKeyName retorna vacío
                if keyName = ""
                    keyName := VK_FALLBACK.Has(vKey) ? VK_FALLBACK[vKey] : Format("vk{:02X}", vKey)
                keyFH.WriteLine(ts . ",KEY_DOWN," . keyName . "," . Format("{:02X}", vKey))
            }
        }
    }
}

; ── Tracking de posición de mouse (16 Hz) ─────────────────────────
TrackMouse() {
    global mouseFH, lastX, lastY
    MouseGetPos(&x, &y)
    if (x != lastX || y != lastY) {
        mouseFH.WriteLine(NowMs() . ",MOVE," . x . "," . y . ",")
        lastX := x
        lastY := y
    }
}

; ── Tracking de frames para video_timeline.csv (~16 Hz) ──────────
TrackTimeline() {
    global videoFH
    videoFH.WriteLine(NowMs() . ",FRAME")
}

; ── Salida ordenada — escribe ANCHOR_END y cierra handles ─────────
GracefulExit() {
    global mouseFH, deltaFH, keyFH, videoFH, stopFile
    ts := NowMs()
    mouseFH.WriteLine(ts . ",ANCHOR_END,,,")
    deltaFH.WriteLine(ts . ",ANCHOR_END,,")
    keyFH.WriteLine(ts   . ",ANCHOR_END,,")
    videoFH.WriteLine(ts . ",ANCHOR_END")
    mouseFH.Close()
    deltaFH.Close()
    keyFH.Close()
    videoFH.Close()
    try FileDelete stopFile
    ExitApp()
}

; ── Polling del stop file (~5 Hz) ─────────────────────────────────
CheckStop() {
    if FileExist(stopFile)
        GracefulExit()
}

; ════════════════════════════════════════════════════════════════════
;  INICIO
; ════════════════════════════════════════════════════════════════════

; 1. Inicializar timer de alta precisión
InitTimer()

; 2. Abrir archivos CSV (append mode para que Python haya podido
;    escribir el header + ANCHOR_START antes de lanzar este script)
mouseFH := FileOpen(mouseFile, "a", "UTF-8")
deltaFH := FileOpen(deltaFile, "a", "UTF-8")
keyFH   := FileOpen(keyFile,   "a", "UTF-8")
videoFH := FileOpen(videoFile, "a", "UTF-8")

; Si los archivos son nuevos (Python no los creó aún), escribir headers
if FileGetSize(mouseFile) < 10 {
    mouseFH.WriteLine("timestamp_ms,event_type,x,y,button")
    deltaFH.WriteLine("timestamp_ms,event_type,dx,dy")
    keyFH.WriteLine("timestamp_ms,event_type,key,vk_code")
    videoFH.WriteLine("timestamp_ms,event_type")
}

; 3. Leer anchor timestamp (escrito por pleiada_app.pyw)
anchorTs   := 0
anchorFile := A_Temp . "\pleiada_anchor_ts.txt"
waitAnchor := 0
while !FileExist(anchorFile) && waitAnchor < 50 {
    Sleep(100)
    waitAnchor++
}
if FileExist(anchorFile) {
    try {
        content  := FileRead(anchorFile)
        anchorTs := Integer(Trim(content))
    }
    try FileDelete anchorFile
}
if anchorTs == 0
    anchorTs := NowMs()

; 4. Escribir ANCHOR_START en los 4 CSVs
mouseFH.WriteLine(anchorTs . ",ANCHOR_START,,,")
deltaFH.WriteLine(anchorTs . ",ANCHOR_START,,")
keyFH.WriteLine(anchorTs   . ",ANCHOR_START,,")
videoFH.WriteLine(anchorTs . ",ANCHOR_START")

; 5. Registrar Raw Input y arrancar timers
RegisterRawInput()
SetTimer(TrackMouse,    62)    ; ~16 Hz
SetTimer(TrackTimeline, 62)    ; ~16 Hz
SetTimer(CheckStop,    200)    ; ~5 Hz — escucha señal de stop

; 6. Listener para WM_INPUT
OnMessage(0x00FF, HandleRawInput)

; 7. Mantener vivo hasta que el padre lo mate
Persistent()
