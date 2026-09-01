# Firma de código con SSL.com (eSigner) — runbook

> Cómo quedan firmados `PleiadaRecorder_Setup.exe` y `PleiadaRecorder_Update.exe`
> en cada release de producción, y qué hay que hacer una sola vez para activarlo.
> Escrito 2026-09-01, a partir del certificado **orden `co-431kv1dia0e`**.

---

## 0. Qué resuelve esto y qué NO

**Qué resuelve.** Antes el instalador salía sin firmar y Windows lo mostraba
como *"Editor desconocido"*. Firmado, Windows lee la firma y muestra el nombre
de la organización: el .exe deja de ser anónimo y cualquiera puede verificar que
lo compilamos nosotros y que nadie lo tocó en el camino.

**Qué NO resuelve — leer antes de prometerle nada a nadie.** Es un certificado
**OV** (confirmado en el portal: `certificate type: Code Signing`,
`validation level: organization`), no EV. Con OV, SmartScreen **no** deja de
advertir el primer día: la reputación se acumula por certificado a medida que la
gente descarga e instala, sin umbral público ni plazo garantizado. Verificado en
una máquina real el 01-09-2026 — el cartel *"Windows protegió su PC"* sigue
apareciendo. Lo que cambió es que la línea `Editor:` ya no dice "desconocido".
El EV es el que arranca con reputación desde el día uno.

### ⚠ El nombre que ve el usuario NO es la marca

El certificado se emitió a nombre de **PLAYDATA SAS**, con `O=Pleiada`. Windows
muestra el Subject completo del certificado, así que el cartel de SmartScreen
dice, textual:

```
Editor: AR, Autonomous City Of Buenos Aires, Buenos Aires, Pleiada, PLAYDATA SAS
```

Eso deja tres nombres distintos de cara al usuario, y ninguno es el producto:

| Dónde | Qué ve el usuario |
|---|---|
| Cartel de SmartScreen | `AR, ..., Pleiada, PLAYDATA SAS` (del certificado) |
| Programas y características | Sunrise Advisors Generation Ltd (`AppPublisher` de `setup.iss`) |
| La app | Gameplay Recorder |

**Esto no se arregla con código.** El Subject está firmado por SSL.com: no hay
flag de `signtool` ni de Inno que lo cambie. La única vía es reemitir el
certificado, y si Sunrise es una entidad legal distinta de PLAYDATA SAS eso es
una orden nueva con validación OV desde cero.

**Decisión de Martín (01-09-2026): se deja para más adelante.** Por eso
`AppPublisher` tampoco se tocó — alinearlo hoy a PLAYDATA SAS significaría
cambiarlo de nuevo si el certificado se reemite.

> El costo de postergarlo: la reputación de SmartScreen se acumula **por
> certificado**. Reemitir más adelante reinicia el contador, así que lo que se
> gane firmando releases con este certificado se pierde el día que se cambie.

**Tampoco cubre:**

- Los builds **locales** (`BuildPleiadaSetup.ps1` o `ISCC` a mano) siguen saliendo
  sin firmar. Los testers de QA van a seguir viendo el cartel. Ver §7.
- El **desinstalador** (`unins000.exe`, que Inno genera en la máquina del usuario)
  queda sin firmar. No es lo que la gente descarga, así que no es lo que dispara
  SmartScreen. Ver §7.
- Los `.pyw` / `.py` de la app no se firman: no son ejecutables PE.

---

## 1. Cómo quedó implementado

Todo pasa en `.github/workflows/build.yml`, en el runner de Windows, entre
compilar y publicar. Cuatro pasos nuevos:

| # | Paso | Qué hace |
|---|---|---|
| 9 | `Check signing secrets` | Verifica que estén los 4 secrets. **Si falta alguno y el build viene de un tag, falla el build**: un release de producción no sale sin firmar. Si no es un tag, avisa y sigue sin firmar. |
| 10 | `Download CodeSignTool` | Baja `CodeSignTool-v1.3.2-windows.zip` desde el repo oficial `SSLcom/CodeSignTool` (204 MB, trae su propio Java). Versión clavada a propósito. |
| 11 | `Sign installers with eSigner` | Firma los dos .exe contra el HSM en la nube de SSL.com y reemplaza los originales en `Output\`. |
| 12 | `Verify Authenticode signature` | Relee los .exe con `Get-AuthenticodeSignature`, muestra firmante y timestamp, y **falla si alguno quedó sin firmar**. |

### El orden importa, y es la parte frágil

La firma **cambia los bytes del .exe**. El paso 15 (`Generate update manifest`)
calcula los SHA-256 que van al `latest.json`, y la app instalada verifica ese
hash antes de ejecutar el updater (`pleiada_app.pyw`, `_upd_download_worker`).

> Si alguna vez alguien mueve la firma después del manifiesto, el hash del
> `latest.json` no va a coincidir con el archivo publicado, la app va a
> **descartar la descarga en silencio** y nadie se va a poder actualizar. El
> release va a verse perfecto en GitHub. Hay un comentario en el YAML avisando
> esto en los dos pasos.

### Por qué CodeSignTool y no la GitHub Action de SSL.com

SSL.com publica `SSLcom/esigner-codesign`. No la usamos por tres razones: su
documentación y todos sus ejemplos son de runners **Ubuntu** (nuestro build es
`windows-latest` y no hay soporte de Windows documentado), la referencia oficial
apunta a la rama `@develop` —una rama móvil con acceso a nuestras credenciales de
firma—, y CodeSignTool nos deja clavar una versión exacta y hacer todo en
PowerShell explícito, igual que el resto del workflow.

---

## 2. Activar el certificado en SSL.com (una sola vez)

⚠ **Antes de empezar:** el QR con el *secret code* se muestra **una sola vez** al
crear el PIN. Si se recarga la página desaparece. Tener el bloc de notas abierto
antes de llegar al paso 4. (Si ya pasó, se puede volver a mostrar — paso 5.)

> Etiquetas verificadas en el portal el 01-09-2026. Si SSL.com rediseña la
> página pueden cambiar, pero el flujo es este.

1. Entrar a **https://secure.ssl.com/certificate_orders/co-431kv1dia0e** con la
   cuenta de SSL.com. La orden figura como `issued` / `(eSigner active)`.
2. Abrir **CERTIFICATE DETAILS**. A la derecha, debajo de los botones
   `SHOW MY SIGNING CREDENTIALS` e `INVITE USERS`, está el bloque
   **eSigner.com Cloud Signing Enrollment**.
3. El desplegable **`Second factor authentication`** tiene que quedar en
   **`OTP APP`**.
   - **No elegir SMS.** El CI necesita un secreto TOTP para generar los códigos
     solo; con SMS habría que firmar a mano cada release.
4. Llenar **`set 4 digit PIN`** y **`confirm PIN`** con el mismo PIN de 4
   dígitos, y tocar el botón **`create OTP`**.
   - **Anotar el PIN antes de seguir.** El portal avisa que hace falta para
     reemplazar o quitar dispositivos de firma, y es lo que permite volver a
     mostrar el QR.
   - Después de unos segundos aparece el **QR code**.
5. **Escanear el QR con Google Authenticator o Authy** (el portal lo pide
   inmediatamente) y después **copiar el `secret code` completo**: es el TOTP
   secret, una cadena larga que termina en `=`, tipo
   `ii5gVvZ9G+WkxB3FauAnoL/z14AXSMistcE0jZMWWNSjQDlql2kt2D6Z+l8=`.
   - **Copiarlo entero, con el `=` final.** Al seleccionar con el mouse se corta
     el último carácter y después el CI falla con "Invalid OTP" sin explicar por qué.
   - Si el QR ya no está: escribir el PIN de 4 dígitos y tocar **Show QR Code**.
6. **Buscar el `credential ID`**: botón verde **`SHOW MY SIGNING CREDENTIALS`**.
   Es un UUID (tipo `fe537ace-e132-52a9-c2e7-egcd2ac3f1e6`).

Al terminar tenés que tener estas cuatro cosas anotadas:

| Dato | De dónde sale |
|---|---|
| Usuario de SSL.com | lo que se tipea en el campo de usuario del login |
| Contraseña de SSL.com | la de la cuenta |
| `credential ID` | sección **SIGNING CREDENTIALS** de la orden |
| `secret code` (TOTP) | el recuadro debajo del QR |

⚠ **Sobre la contraseña:** CodeSignTool se invoca a través de un `.bat`, y `cmd`
se come o rompe algunos caracteres. Si la contraseña de SSL.com tiene
**`&` `%` `^` `<` `>` `|`**, cambiala en el portal por una sin esos símbolos antes
de seguir. Es la causa número uno de "usuario o contraseña incorrectos" en CI con
credenciales que andan bien en el navegador.

---

## 3. Cargar los secrets en GitHub (una sola vez)

Los 4 valores van como **repository secrets** del repo
`PleiadaAI/pleiada-recorder`.

⚠ El repo es **público**, pero los secrets no se exponen: el workflow solo corre
en `push` de tags y en `workflow_dispatch` (no en `pull_request`), y GitHub
enmascara los valores en los logs. Aun así: **nunca** pegar estos valores en un
issue, un commit o un `Write-Host`.

1. Ir a **https://github.com/PleiadaAI/pleiada-recorder/settings/secrets/actions**
2. Botón **New repository secret** (arriba a la derecha).
3. Cargar los cuatro, uno por uno. Los nombres tienen que ser **exactos**:

| Name | Secret |
|---|---|
| `ES_USERNAME` | usuario de SSL.com |
| `ES_PASSWORD` | contraseña de SSL.com |
| `ES_CREDENTIAL_ID` | el credential ID (UUID) |
| `ES_TOTP_SECRET` | el secret code del QR |

4. Verificar que en la lista aparezcan los 4 con esos nombres escritos igual.
   Un nombre mal escrito no da error: el build simplemente falla en el paso 9 con
   *"Faltan secretos de firma"*.

---

## 4. Probar la firma SIN publicar nada

Esto es lo primero que hay que hacer, antes de cualquier tag. El workflow tiene
`workflow_dispatch`, y **todos** los pasos que publican (manifiesto, release,
borrado de assets viejos) están condicionados a `startsWith(github.ref,
'refs/tags/')`. O sea: un run manual compila y firma, sube el artifact y **no
toca producción**.

1. Ir a
   **https://github.com/PleiadaAI/pleiada-recorder/actions/workflows/build.yml**
2. Botón **Run workflow** (arriba a la derecha) → elegir la rama en
   **`Use workflow from`** → **Run workflow**.
   - ⚠ Si se deja en `main` cuando el cambio está en una rama, corre el workflow
     de `main` y no se prueba nada.
3. Esperar ~3 min y abrir el run.
4. **Qué mirar, en este orden:**
   - Paso **Check signing secrets** → tiene que decir
     `Secretos de firma presentes: se van a firmar los dos instaladores.`
   - Paso **Sign installers with eSigner** → dos líneas
     `OK: ... firmado y reemplazado en Output\`
   - Paso **Verify Authenticode signature** → tiene que decir `Valid` en los dos
     y mostrar `Firmante: CN=PLAYDATA SAS, O=Pleiada, ...` más una línea
     `Timestamp: CN=SSL.com Timestamping Unit ...`.
   - Paso **Verify output** → `PleiadaRecorder_Setup.exe (181 MB)` y
     `PleiadaRecorder_Update.exe (2.2 MB)`. Un tamaño muy distinto en el completo
     significa que faltó algo en `deps\`.
5. Bajar el artifact del run (sección **Artifacts**, al final de la página; viene
   como .zip con los dos .exe) y probar el completo en una máquina limpia.

**Resultado real del 01-09-2026** (run `33568429344`), para que sirva de
referencia: SmartScreen **sí** apareció, y la línea `Editor:` mostró
`AR, Autonomous City Of Buenos Aires, Buenos Aires, Pleiada, PLAYDATA SAS`.
Eso es lo esperado con un certificado OV recién emitido — ver §0.

Para chequearlo desde PowerShell en tu PC, sobre el .exe bajado:

```bash
Get-AuthenticodeSignature "$env:USERPROFILE\Downloads\PleiadaRecorder_Setup.exe" | Format-List Status, StatusMessage, SignerCertificate, TimeStamperCertificate
```

`Status` tiene que ser `Valid`.

**Si el paso 12 dice `Valid` pero `Timestamp:` no aparece**, avisar: significa que
la firma deja de validar el día que vence el certificado (01/09/2027), incluso en
los instaladores ya distribuidos. El workflow lo marca como *warning*, no falla.

---

## 5. El primer release firmado

Una vez que el paso 4 dio verde, el proceso de release **no cambia**: sigue siendo
el de [`COMO_PUBLICAR_ACTUALIZACIONES.md`](COMO_PUBLICAR_ACTUALIZACIONES.md). La
firma pasa sola al pushear el tag.

Dos cosas propias de este primer release:

1. **Versión nueva.** Los .exe firmados son bytes distintos a los sin firmar, así
   que es un build distinto y le toca número nuevo (regla del proyecto: nunca dos
   builds con el mismo número). La firma entra en el primer tag que salga después
   de mergear esta rama a `main`; no hace falta un bump extra por la firma en sí.
2. **CHANGELOG.** Es un cambio que el usuario ve, así que va una línea — y como
   todo copy visible, **la confirma Martín antes de publicar**. Propuesta para
   pegar en la sección de la versión:

```
### El instalador ahora está firmado

Windows ya no lo marca como de editor desconocido: al instalarlo podés ver la
organización que lo publica y verificar que el archivo es el que publicamos
nosotros y que nadie lo modificó por el camino.

Windows puede seguir mostrando una advertencia las primeras veces, hasta que
reconozca la firma como conocida. Si aparece, "Más información" y "Ejecutar de
todas formas".
```

⚠ Esa propuesta evita nombrar a la organización a propósito, porque hoy el
certificado dice PLAYDATA SAS y `AppPublisher` dice Sunrise (ver §0). Si el
certificado se reemite, revisar si conviene nombrarla.

---

## 6. Fechas que hay que vigilar

| Fecha | Qué pasa | Qué hacer |
|---|---|---|
| **01/10/2026** | Se terminan los **30 días de firmas de cortesía** que arrancaron el 01/09/2026 con la emisión. | Confirmar en la cuenta de SSL.com cuántas firmas incluye el plan de acá en adelante. Cada release consume **2 firmas** (Setup + Update), así que el consumo es bajísimo, pero si la cuota se agota **el build del tag falla en el paso 11** y no sale el release. Eso es a propósito: preferimos un release que no sale a uno que sale sin firmar. |
| **01/09/2027** | **Vence el certificado** (1 año desde la emisión). | Renovar antes. Los instaladores ya publicados siguen validando gracias al timestamp; los builds nuevos fallarían. |

---

## 7. Lo que quedó afuera a propósito

- **Builds locales sin firmar.** `BuildPleiadaSetup.ps1` y el `ISCC` a mano
  producen .exe sin firma, así que QA sigue viendo el cartel de Windows. Se puede
  resolver instalando **eSigner CKA** en la máquina de build (mete el certificado
  en el almacén de Windows y `signtool.exe` lo usa como si fuera un token USB),
  pero es una fase aparte: hay que instalarlo, dejar las credenciales en un
  archivo local y sumar la directiva `SignTool` a `setup.iss`. No es necesario
  para lo que se pidió (producción).
- **Desinstalador sin firmar.** Firmarlo requiere que Inno lo firme en tiempo de
  compilación (`SignTool=` + `SignedUninstaller=yes`), o sea meter CodeSignTool
  adentro del ISCC. Suma una firma más por build y no cambia nada de lo que ve el
  usuario al descargar.

---

## 8. Si falla

| Síntoma en el log | Causa probable | Arreglo |
|---|---|---|
| Paso 9: `Faltan secretos de firma: ...` | Un secret no está cargado o el nombre está mal escrito. | Revisar §3. Los nombres son case-sensitive. |
| Paso 11: `Invalid credentials` / `Authentication failed` | Contraseña con `& % ^ < > \|`, o usuario mal. | Cambiar la contraseña en SSL.com por una sin esos símbolos y actualizar `ES_PASSWORD`. |
| Paso 11: `Invalid OTP` / `Invalid TOTP` | El `secret code` está incompleto o mal copiado (suele cortarse el `=` final). | Volver al portal, **Show QR Code** con el PIN, copiar de nuevo entero. |
| Paso 11: `Credential ID not found` | El UUID es de otra orden, o la orden no está enrolada en eSigner. | Revisar la sección **SIGNING CREDENTIALS** de la orden `co-431kv1dia0e`. |
| Paso 11: `CodeSignTool no genero el firmado de ...` sin error claro | Cuota de firmas agotada, o el servicio de SSL.com caído. | Ver §6. Reintentar el run; si persiste, escribir a soporte de SSL.com con el número de orden. |
| Paso 12: `NotSigned` | CodeSignTool devolvió 0 pero no firmó (le pasa). | El build falla solo, que es lo correcto. Mirar el log del paso 11 buscando el error real. |
| El release salió pero nadie se actualiza | Alguien movió el paso de la firma después del manifiesto y los SHA-256 no coinciden. | Ver §1. Publicar una versión nueva con el orden corregido. |

---

## Fuentes

- [eSigner CodeSignTool Command Guide — SSL.com](https://www.ssl.com/guide/esigner-codesigntool-command-guide/)
- [Remote EV Code Signing with eSigner — SSL.com](https://www.ssl.com/guide/remote-ev-code-signing-with-esigner/)
- [Automate eSigner EV Code Signing — SSL.com](https://www.ssl.com/how-to/automate-esigner-ev-code-signing/)
- [Cloud Code Signing Integration with GitHub Actions — SSL.com](https://www.ssl.com/how-to/cloud-code-signing-integration-with-github-actions/)
- [SSLcom/CodeSignTool — releases](https://github.com/SSLcom/CodeSignTool/releases)
- [SSLcom/esigner-codesign — la Action que decidimos no usar](https://github.com/SSLcom/esigner-codesign)
