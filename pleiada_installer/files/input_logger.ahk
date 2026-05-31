#Requires AutoHotkey v2.0
#SingleInstance Off

; ══════════════════════════════════════════════════════════════════
;  PLEIADA — Input Logger V2 (headless)
;  Uso: AutoHotkey64.exe input_logger.ahk "<logDir>" ["<gameExe>"]
;
;  v0.5 — Captura robusta en FULLSCREEN EXCLUSIVO:
;    • Teclado      → low-level keyboard hook (InputHook / WH_KEYBOARD_LL)
;    • Botones+rueda→ low-level mouse hooks (hotkeys ~* con InstallMouseHook)
;    • Deltas mouse → Raw Input (WM_INPUT), re-registrado para enganchar
;                     aunque el juego ya esté en fullscreen exclusivo al arrancar.
;
;  Motivo: RIDEV_INPUTSINK no recibe WM_INPUT cuando se registra mientras una
;  app está en fullscreen EXCLUSIVO (ej: motor Prism3D de ETS2). Los hooks
;  low-level operan en el hook-chain del sistema y sí capturan en ese modo.
;  El formato de salida (CSVs, campos, ANCHOR, NowMs) es idéntico a V1.
; ══════════════════════════════════════════════════════════════════

; ── Directorio de sesión ──────────────────────────────────────────
global logDir := A_Args.Length > 0 ? A_Args[1] : ""

if logDir = "" {
    ExitApp()
}

; ── PLE-43/13: exe del juego para filtrar inputs por ventana activa ──────────
; Si se recibe como segundo argumento, solo se loggea cuando ese proceso está en foco.
; Si está vacío, se loggea todo (sin restricción).
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
global keyHook     := 0
global reRegCount  := 0

; ── PLE-25: mapa de nombres para teclas OEM que GetKeyName retorna vacío ──────
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

; ── Filtro de ventana activa (PLE-43) ─────────────────────────────
GameActive() {
    global gameExe
    return gameExe = "" || WinActive("ahk_exe " . gameExe)
}

; ═══════════════════════════════════════════════════════════════════
;  TECLADO — low-level keyboard hook vía InputHook (WH_KEYBOARD_LL)
;  Funciona en fullscreen exclusivo. Formato de salida idéntico a V1.
; ═══════════════════════════════════════════════════════════════════

SetupKeyboardHook() {
    global keyHook
    keyHook := InputHook("V L0 I0")   ; V=no bloquea, L0=sin límite, I0=no ignora
    keyHook.KeyOpt("{All}", "N")       ; N = notificar down y up de TODAS las teclas
    keyHook.OnKeyDown := KeyDownHandler
    keyHook.OnKeyUp   := KeyUpHandler
    keyHook.Start()
}

_KeyName(vk) {
    global VK_FALLBACK
    n := GetKeyName(Format("vk{:02X}", vk))
    if n = ""
        n := VK_FALLBACK.Has(vk) ? VK_FALLBACK[vk] : Format("vk{:02X}", vk)
    return n
}

KeyDownHandler(ih, vk, sc) {
    global keyFH, pressedKeys
    if !GameActive()
        return
    if vk == 0 || vk == 0xFF
        return
    if pressedKeys.Has(vk)        ; anti-repeat: ignorar auto-repeat
        return
    pressedKeys[vk] := true
    keyFH.WriteLine(NowMs() . ",KEY_DOWN," . _KeyName(vk) . "," . Format("{:02X}", vk))
}

KeyUpHandler(ih, vk, sc) {
    global keyFH, pressedKeys
    if vk == 0 || vk == 0xFF
        return
    if !pressedKeys.Has(vk)
        return
    pressedKeys.Delete(vk)
    ; KEY_UP se registra aunque el juego pierda foco, para cerrar el evento abierto.
    keyFH.WriteLine(NowMs() . ",KEY_UP," . _KeyName(vk) . "," . Format("{:02X}", vk))
}

; ═══════════════════════════════════════════════════════════════════
;  MOUSE BOTONES + RUEDA — low-level mouse hook (hotkeys ~* )
;  ~ = pasa el evento al juego (no lo bloquea), * = cualquier modificador.
;  InstallMouseHook fuerza WH_MOUSE_LL → captura en fullscreen exclusivo.
; ═══════════════════════════════════════════════════════════════════

MouseBtn(evtType, btn) {
    global mouseFH
    if !GameActive()
        return
    MouseGetPos(&cx, &cy)
    mouseFH.WriteLine(NowMs() . "," . evtType . "," . cx . "," . cy . "," . btn)
}

MouseScroll(delta) {
    global mouseFH
    if !GameActive()
        return
    MouseGetPos(&cx, &cy)
    mouseFH.WriteLine(NowMs() . ",SCROLL," . cx . "," . cy . "," . delta)
}

~*LButton::      MouseBtn("BUTTON_DOWN", "LEFT")
~*LButton Up::   MouseBtn("BUTTON_UP",   "LEFT")
~*RButton::      MouseBtn("BUTTON_DOWN", "RIGHT")
~*RButton Up::   MouseBtn("BUTTON_UP",   "RIGHT")
~*MButton::      MouseBtn("BUTTON_DOWN", "MIDDLE")
~*MButton Up::   MouseBtn("BUTTON_UP",   "MIDDLE")
~*XButton1::     MouseBtn("BUTTON_DOWN", "X1")
~*XButton1 Up::  MouseBtn("BUTTON_UP",   "X1")
~*XButton2::     MouseBtn("BUTTON_DOWN", "X2")
~*XButton2 Up::  MouseBtn("BUTTON_UP",   "X2")
~*WheelUp::      MouseScroll(120)
~*WheelDown::    MouseScroll(-120)

; ═══════════════════════════════════════════════════════════════════
;  DELTAS DE MOUSE — Raw Input (WM_INPUT), solo movimiento relativo.
;  Los botones NO se procesan acá (van por hook) para evitar duplicados.
; ═══════════════════════════════════════════════════════════════════

RegisterRawInput() {
    ; Solo mouse (usage page 1, usage 2) con RIDEV_INPUTSINK.
    rid := Buffer(16, 0)
    NumPut("UShort", 1,     rid, 0)
    NumPut("UShort", 2,     rid, 2)
    NumPut("UInt",   0x100, rid, 4)    ; RIDEV_INPUTSINK
    NumPut("Ptr", A_ScriptHwnd, rid, 8)
    DllCall("RegisterRawInputDevices", "Ptr", rid, "UInt", 1, "UInt", 16)
}

; Re-registrar Raw Input los primeros segundos. Si al arrancar el juego ya
; estaba en fullscreen exclusivo, el primer registro puede no enganchar;
; reintentar asegura que el sink reciba WM_INPUT una vez estabilizado.
ReRegisterRawInput() {
    global reRegCount
    RegisterRawInput()
    reRegCount++
    if reRegCount >= 6
        SetTimer(ReRegisterRawInput, 0)   ; detener tras ~6 reintentos
}

HandleRawInput(wParam, lParam, msg, hwnd) {
    global deltaFH
    if !GameActive()
        return

    cbSize := 0
    DllCall("GetRawInputData", "Ptr", lParam, "UInt", 0x10000003,
            "Ptr", 0, "UInt*", &cbSize, "UInt", 24)
    if cbSize == 0
        return

    buf := Buffer(cbSize, 0)
    if DllCall("GetRawInputData", "Ptr", lParam, "UInt", 0x10000003,
               "Ptr", buf, "UInt*", &cbSize, "UInt", 24) == 0
        return

    if NumGet(buf, 0, "UInt") != 0   ; dwType != 0 → no es mouse
        return

    usFlags := NumGet(buf, 24, "UShort")
    lLastX  := NumGet(buf, 36, "Int")
    lLastY  := NumGet(buf, 40, "Int")

    ; Movimiento relativo → mouse_delta_log.csv (igual que V1)
    if (lLastX != 0 || lLastY != 0) && !(usFlags & 0x01)
        deltaFH.WriteLine(NowMs() . ",MOVE," . lLastX . "," . lLastY)
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
    global mouseFH, deltaFH, keyFH, videoFH, stopFile, keyHook
    try keyHook.Stop()
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

; 2. Abrir archivos CSV (append mode)
mouseFH := FileOpen(mouseFile, "a", "UTF-8")
deltaFH := FileOpen(deltaFile, "a", "UTF-8")
keyFH   := FileOpen(keyFile,   "a", "UTF-8")
videoFH := FileOpen(videoFile, "a", "UTF-8")

; Si los archivos son nuevos, escribir headers
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

; 5. Instalar hooks low-level (forzar WH_KEYBOARD_LL y WH_MOUSE_LL)
InstallKeybdHook()
InstallMouseHook()
SetupKeyboardHook()

; 6. Registrar Raw Input (deltas de mouse) + re-registro robusto
RegisterRawInput()
OnMessage(0x00FF, HandleRawInput)
SetTimer(ReRegisterRawInput, 1000)   ; reintenta el registro los primeros segundos

; 7. Timers de polling
SetTimer(TrackMouse,    62)    ; ~16 Hz — posición absoluta
SetTimer(TrackTimeline, 62)    ; ~16 Hz — frames
SetTimer(CheckStop,    200)    ; ~5 Hz — señal de stop

; 8. Mantener vivo hasta que el padre lo mate
Persistent()
