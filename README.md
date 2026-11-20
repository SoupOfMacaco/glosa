<p align="center">
  <img src="assets/logo.png" width="128" alt="Logo de Glosa">
</p>

<h1 align="center">Glosa</h1>
<p align="center"><b>Traductor de escritorio en tiempo real</b> · gratis · Windows 10 y 11</p>

> **¿Por qué "Glosa"?** Una glosa es una nota que se escribe junto a un texto para explicarlo o traducirlo. Las *Glosas Emilianenses*, anotaciones al margen de un texto en latín, se consideran de los primeros escritos en español. Esta app hace lo mismo: pone la traducción encima del texto, como una nota flotante.

**Glosa es un traductor de escritorio en tiempo real.** Marcas una o varias zonas de la pantalla y Glosa lee en vivo el texto en inglés que aparece en ellas. Te muestra la traducción al español en una ventana flotante, encima del texto o en una esquina, sin pulsar nada cada vez que cambia el texto.

Sirve para cualquier cosa que tenga texto en pantalla:

- **Día a día:** programas, páginas o aplicaciones que solo están en inglés, chats, notificaciones.
- **Trabajo y estudios:** documentación, herramientas o cursos en otro idioma (también dentro de empresas, ver la [licencia](#licencia-libre-para-usar-prohibido-venderla)).
- **Juegos:** diálogos, misiones y menús, con perfiles que se activan solos según el juego.
- **Y más:** vídeos con subtítulos incrustados, emuladores, novelas visuales...

Se queda en segundo plano, junto al reloj, mientras usas el ordenador.

```
 ┌───────────────────────────────────────────────┐   ┌──────────────────────────────┐
 │ ¡Si sobrevivimos a esto, nos vengaremos!      │   │ ¡Si sobrevivimos a esto,     │
 ├───────────────────────────────────────────────┤   │  nos vengaremos de ellos!    │
 │ Mercenary                                     │   │ If we survive this, we'll... │
 │ If we survive this, we'll get back at them!   │   │                  vía Google  │
 └───────────────────────────────────────────────┘   └──────────────────────────────┘
        modo flotante (encima del texto)                   modo esquina
```

## Descarga e instalación

1. Ve a [**Releases**](https://github.com/SoupOfMacaco/glosa/releases/latest) y descarga `Glosa-Setup-X.Y.Z.exe`.
2. Ejecútalo. Se instala solo para tu usuario y **no necesita administrador**. Si a tu Windows le falta el OCR en inglés, el instalador trae una casilla marcada para instalarlo; ese paso sí pide permiso de administrador, una sola vez. Al terminar, ya está todo listo para usar.
3. Al abrirla por primera vez te explica los atajos y te pide marcar la zona del texto.

> Windows SmartScreen puede avisar de que el programa "no es reconocido" porque no está firmado digitalmente (los certificados cuestan dinero). Pulsa **Más información → Ejecutar de todas formas**. El código está entero en este repositorio.

## Cómo se usa

1. Pon el juego en **modo ventana** o **ventana sin bordes** (ver limitaciones).
2. Con el juego en primer plano, pulsa **Ctrl+Shift+T** y arrastra un rectángulo sobre cada zona donde salga texto. Puedes marcar **varias**, por ejemplo los diálogos de arriba y los de abajo. Pulsa **Enter** para guardar.
3. Listo: cada vez que cambie el texto de cualquier zona, aparecerá su traducción.

En el editor de zonas: **clic derecho** sobre una zona la quita, **Retroceso** quita la última, **Supr** las quita todas y **Esc** cancela sin guardar.

| Atajo | Acción |
|---|---|
| `Ctrl+Shift+T` | Editar las zonas del perfil (una o varias) |
| `Ctrl+Shift+O` | Cambiar al siguiente perfil |
| `Ctrl+Shift+P` | Pausar / reanudar |
| `Ctrl+Shift+M` | Cambiar el modo: flotante, esquina o ambos |
| `Ctrl+Shift+H` | Ocultar / mostrar la traducción |

Todo lo demás está en el menú del icono de la bandeja (clic derecho): perfiles, ajustes, buscar actualizaciones, abrir la carpeta de datos y salir.

### Perfiles por programa o juego

Cada juego o programa pone el texto en un sitio distinto, así que las zonas se guardan en **perfiles**:

- Si pulsas `Ctrl+Shift+T` **desde el juego**, las zonas se guardan en un perfil vinculado a ese juego (por su `.exe`), con el nombre de su ventana. Si ese juego no tenía perfil, se crea uno.
- La próxima vez que abras ese juego, **Glosa cambia sola a su perfil** en cuanto la ventana del juego pasa a primer plano.
- Desde la bandeja (**Perfiles**) puedes cambiar de perfil a mano, crear uno nuevo, renombrarlo, vincularlo o desvincularlo de un juego, eliminarlo, o desactivar el cambio automático.
- Los perfiles se guardan en `%APPDATA%\Glosa\config.json`.

## Qué hace

- **Lectura en vivo continua.** Revisa la zona varias veces por segundo (cada 250 ms por defecto, ajustable). No hay que recargar ni pulsar nada.
- **Varias zonas a la vez**, cada una con su propio lector, y **perfiles por juego** que se activan solos.
- **No traduce lo que ya está en español**: si una zona muestra texto que ya está en el idioma de destino, no aparece ninguna traducción.
- **Ignora la basura del OCR**, como las líneas sin sentido que salen de bordes y adornos del cuadro de diálogo.
- **Detecta el texto que se escribe letra a letra** y espera a que termine antes de traducir, para no traducir frases a medias. Si el fondo está siempre animado, lee igualmente cada pocos segundos.
- **No repite trabajo**: si el texto no cambia, no se vuelve a leer ni a traducir.
- **Traducción híbrida (con y sin internet):**
  1. **Memoria local**: cada frase traducida se guarda y la próxima vez sale al instante, sin internet. La memoria crece sola mientras juegas.
  2. **Glosario incluido** con unas 100 frases típicas de juegos (menús, combate, etc.).
  3. **Traducción online gratuita**: Google Translate y, si falla, MyMemory.
  4. **Sin conexión**: muestra el texto original con un aviso y reintenta cada 5 segundos.
- **Dos formas de mostrar la traducción**, o las dos a la vez:
  - **Flotante**: sobre el texto original, ya sea tapándolo o justo encima.
  - **Esquina**: en la esquina que elijas, con el texto original debajo si quieres. Con varias zonas, se apila un bloque por zona, etiquetado como "Zona 1", "Zona 2"...
- **La traducción no estorba al OCR.** Las ventanas de traducción están excluidas de las capturas de pantalla, así que la app nunca lee su propia traducción, aunque tape el texto original.
- **Corrige errores típicos del OCR** con fuentes pixeladas (por ejemplo `suyvive` → `survive`).
- **Las ventanas de traducción no reciben clics**: el ratón pasa a través, al juego.
- **Actualizaciones automáticas.** Al iniciar comprueba si hay una versión nueva en GitHub. Si la hay, te pregunta, la descarga, se actualiza y se vuelve a abrir.
- **Transparencia ajustable**, con vista previa en vivo en Ajustes:
  - **Opacidad del fondo**, de 0 % a 100 %. Al 0 % solo se ve el texto, con un contorno oscuro para que se lea sobre cualquier fondo.
  - **Opacidad del texto**, de 20 % a 100 %, para que la traducción moleste lo menos posible.
- Ajustes: tamaño de letra, esquina, idioma de destino (español, portugués, francés, italiano, alemán), inicio con Windows, etc.

## Qué NO hace (limitaciones)

- **No funciona con juegos en "pantalla completa exclusiva".** Windows no deja dibujar ventanas encima. Usa **ventana sin bordes** (borderless / windowed fullscreen), que casi todos los juegos tienen.
- **No es perfecta leyendo.** El OCR puede fallar alguna letra con fuentes muy estilizadas, texto sobre fondos muy cargados o letras muy pequeñas. Marcar solo el cuadro de texto, sin decoración alrededor, ayuda mucho.
- **La traducción es automática.** A veces sale literal o pierde el tono de un personaje.
- **No lee voz ni subtítulos de vídeo con efectos.** Solo texto visible y estático o que se va escribiendo.
- **El cambio automático de perfil reconoce el juego por su `.exe`.** Si dos juegos usan el mismo ejecutable (por ejemplo, juegos de navegador o emuladores), comparten perfil, así que cambia entre ellos a mano con `Ctrl+Shift+O`.
- **Cada zona consume algo de CPU.** Con 2 o 3 zonas no se nota; con muchas, sube el intervalo en Ajustes.
- **Las ventanas de traducción no salen en grabaciones ni streams** (OBS, capturas de Windows...), porque están excluidas de la captura a propósito. Esto requiere Windows 10 versión 2004 o posterior. En versiones anteriores, el modo "tapando el texto" pasa automáticamente a "justo encima".
- **Sin Linux ni macOS.** Usa el OCR propio de Windows.

## Mejorar la lectura: OCR en inglés

La app usa el OCR que trae Windows. Si tu Windows está en español, lo normal es que solo tenga el OCR en español, que lee el inglés razonablemente bien pero confunde más letras.

Por eso el **instalador lo instala automáticamente** si falta, con la casilla "Instalar el OCR en inglés de Windows", marcada por defecto. Las actualizaciones automáticas nunca vuelven a pedirlo.

Si desmarcaste la casilla, puedes instalarlo después desde **Ajustes → Idioma del OCR → Instalar OCR en inglés…**. Cuando termine, la app empieza a usarlo sola. Las dos opciones equivalen a ejecutar en PowerShell como administrador:

```powershell
Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
```

## Privacidad

- La lectura de pantalla (OCR) se hace **en tu PC**, sin internet. Las imágenes nunca se envían a ningún sitio.
- Solo el **texto reconocido** que no esté ya en la memoria local se envía a Google Translate (o a MyMemory si Google falla) para traducirlo.
- La memoria de traducciones, la configuración y el registro se guardan en `%APPDATA%\Glosa\`. Puedes vaciar la memoria desde Ajustes.
- La comprobación de actualizaciones consulta la API pública de GitHub.

> Los servicios de traducción usados son gratuitos y no oficiales, o con límites diarios: el endpoint público de Google y la API anónima de MyMemory (unas 5000 palabras al día). Si alguno deja de funcionar, la app usa el otro, y la memoria local sigue funcionando siempre.

## Requisitos

- Windows 10 versión 1809 o posterior, o Windows 11, de 64 bits.
- Conexión a internet para traducir frases nuevas (opcional una vez que la memoria las tiene).

## Para desarrolladores

```powershell
git clone https://github.com/SoupOfMacaco/glosa
cd glosa
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python -m app          # ejecutar desde el código
.\build.ps1 -Python .\.venv\Scripts\python   # compilar exe + instalador (requiere Inno Setup 6)
```

`tools/demo_dialog.py` abre una ventana que imita un cuadro de diálogo con texto que se va escribiendo, útil para probar sin abrir un juego. Con `--set-region` la configura como zona a leer. Si lanzas la app con la variable de entorno `TEV_DEBUG_VISIBLE=1`, las ventanas de traducción sí salen en las capturas, para poder depurar.

### Estructura

| Archivo | Qué hace |
|---|---|
| `app/main.py` | Icono de bandeja, menú, atajos y coordinación general |
| `app/worker.py` | Bucle en vivo: captura, detección de cambios, OCR y traducción |
| `app/ocr.py` | OCR de Windows (WinRT) y preprocesado de la imagen |
| `app/textfix.py` | Une líneas en párrafos y corrige errores del OCR |
| `app/translator.py` | Memoria SQLite, glosario y servicios online |
| `app/overlay.py` | Ventanas flotantes (sobre el texto y en la esquina) |
| `app/selector.py` | Editor de zonas con el ratón: varias zonas, multimonitor y DPI |
| `app/config.py` | Ajustes y perfiles (zonas y juego vinculado) |
| `app/updater.py` | Comprobación y descarga de actualizaciones |
| `app/data/glosario.json` | Frases incluidas de serie |
| `installer/setup.iss` | Instalador (Inno Setup) |
| `.github/workflows/release.yml` | Compila y publica cada versión |

### Publicar una versión nueva

1. Cambia `__version__` en `app/__init__.py` (por ejemplo, `1.1.0`).
2. Añade una sección `## [1.1.0]` en `CHANGELOG.md`.
3. Crea y sube la etiqueta:
   ```powershell
   git commit -am "Versión 1.1.0"
   git tag v1.1.0
   git push --follow-tags
   ```
4. GitHub Actions compila el instalador y crea la Release. Las apps instaladas la detectan al iniciar.

## Ideas para el futuro

- Leer la traducción en voz alta (texto a voz).
- Opciones de visualización distintas para cada perfil.
- Más servicios de traducción (DeepL con clave propia, LibreTranslate, modelos locales).
- Editar a mano las traducciones guardadas.

## Licencia: libre para usar, prohibido venderla

Glosa se distribuye bajo la licencia **[PolyForm Shield 1.0.0](LICENSE)**. El código es abierto y **cualquiera puede usarla gratis, también empresas**. Lo que no se permite es **venderla ni ofrecerla como otro producto**.

Resumen orientativo en español (el texto que vale legalmente es el del archivo [LICENSE](LICENSE), en inglés):

| ✅ Se permite | ❌ No se permite |
|---|---|
| Usarla gratis en casa, para estudiar, para jugar... | **Venderla**, revenderla o cobrar por ella |
| **Usarla en empresas y en el trabajo**, por ejemplo para empleados que no dominan el inglés | **Ofrecerla como otro producto** (renombrada, modificada o integrada en un traductor propio), aunque sea gratis |
| Leer el código, modificarlo y adaptarlo para uso propio o de tu empresa | Usar el código para crear un producto o servicio que compita con Glosa |
| Compartirla gratis, siempre con esta licencia y el aviso de copyright | Quitar la licencia o el aviso de copyright al compartirla |

El software se ofrece **tal cual, sin garantías**.

Si quieres hacer algo que la licencia no permite, como integrarla en un producto propio, pide permiso al autor abriendo un *issue* en este repositorio.

> Nota: las versiones 1.0.0 a 1.2.0 se publicaron con licencia MIT, y la 1.3.0 y la 1.3.1 con PolyForm Noncommercial. Desde la 1.3.2, el proyecto usa PolyForm Shield 1.0.0. Esto no es asesoramiento legal.

Copyright © 2026 SoupOfMacaco.
