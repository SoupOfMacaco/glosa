# Traductor en Vivo

Aplicación gratuita para **Windows 10 y 11** que lee en tiempo real el texto en inglés de una zona de la pantalla (por ejemplo, el cuadro de diálogo de un juego) y te muestra la traducción al español en una ventana flotante, sin tener que pulsar nada cada vez que cambia el texto.

Se queda en segundo plano, junto al reloj, mientras juegas.

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

1. Ve a [**Releases**](https://github.com/SoupOfMacaco/traductor-en-vivo/releases/latest) y descarga `TraductorEnVivo-Setup-X.Y.Z.exe`.
2. Ejecútalo. **No pide permisos de administrador**: se instala solo para tu usuario.
3. Al abrirla por primera vez te explica los atajos y te pide marcar la zona del texto.

> Windows SmartScreen puede avisar de que el programa "no es reconocido" porque no está firmado digitalmente (los certificados cuestan dinero). Pulsa **Más información → Ejecutar de todas formas**. El código está entero en este repositorio.

## Cómo se usa

1. Pon el juego en **modo ventana** o **ventana sin bordes** (ver limitaciones).
2. Pulsa **Ctrl+Shift+T** y arrastra un rectángulo sobre el cuadro de diálogo.
3. Listo: cada vez que cambie el texto, aparecerá la traducción.

| Atajo | Acción |
|---|---|
| `Ctrl+Shift+T` | Seleccionar la zona a leer |
| `Ctrl+Shift+P` | Pausar / reanudar |
| `Ctrl+Shift+M` | Cambiar el modo: flotante, esquina o ambos |
| `Ctrl+Shift+H` | Ocultar / mostrar la traducción |

Todo lo demás está en el menú del icono de la bandeja (clic derecho): ajustes, buscar actualizaciones, abrir la carpeta de datos y salir.

## Qué hace

- **Lectura en vivo continua.** Revisa la zona varias veces por segundo (cada 250 ms por defecto, ajustable). No hay que recargar ni pulsar nada.
- **Detecta el texto que se escribe letra a letra** y espera a que termine antes de traducir, para no traducir frases a medias. Si el fondo está siempre animado, lee igualmente cada pocos segundos.
- **No repite trabajo**: si el texto no cambia, no se vuelve a leer ni a traducir.
- **Traducción híbrida (con y sin internet):**
  1. **Memoria local**: cada frase traducida se guarda y la próxima vez sale al instante, sin internet. La memoria crece sola mientras juegas.
  2. **Glosario incluido** con unas 100 frases típicas de juegos (menús, combate, etc.).
  3. **Traducción online gratuita**: Google Translate y, si falla, MyMemory.
  4. **Sin conexión**: muestra el texto original con un aviso y reintenta cada 5 segundos.
- **Dos formas de mostrar la traducción**, o las dos a la vez:
  - **Flotante**: sobre el texto original, ya sea tapándolo o justo encima.
  - **Esquina**: en la esquina que elijas, con el texto original debajo si quieres.
- **La traducción no estorba al OCR.** Las ventanas de traducción están excluidas de las capturas de pantalla, así que la app nunca lee su propia traducción, aunque tape el texto original.
- **Corrige errores típicos del OCR** con fuentes pixeladas (por ejemplo `suyvive` → `survive`).
- **Las ventanas de traducción no reciben clics**: el ratón pasa a través, al juego.
- **Actualizaciones automáticas.** Al iniciar comprueba si hay una versión nueva en GitHub. Si la hay, te pregunta, la descarga, se actualiza y se vuelve a abrir.
- Ajustes: tamaño de letra, opacidad, esquina, idioma de destino (español, portugués, francés, italiano, alemán), inicio con Windows, etc.

## Qué NO hace (limitaciones)

- **No funciona con juegos en "pantalla completa exclusiva".** Windows no deja dibujar ventanas encima. Usa **ventana sin bordes** (borderless / windowed fullscreen), que casi todos los juegos tienen.
- **No es perfecta leyendo.** El OCR puede fallar alguna letra con fuentes muy estilizadas, texto sobre fondos muy cargados o letras muy pequeñas. Marcar solo el cuadro de texto, sin decoración alrededor, ayuda mucho.
- **La traducción es automática.** A veces sale literal o pierde el tono de un personaje.
- **No lee voz ni subtítulos de vídeo con efectos.** Solo texto visible y estático o que se va escribiendo.
- **Una sola zona a la vez.**
- **Las ventanas de traducción no salen en grabaciones ni streams** (OBS, capturas de Windows...), porque están excluidas de la captura a propósito. Esto requiere Windows 10 versión 2004 o posterior. En versiones anteriores, el modo "tapando el texto" pasa automáticamente a "justo encima".
- **Sin Linux ni macOS.** Usa el OCR propio de Windows.

## Mejorar la lectura: OCR en inglés

La app usa el OCR que trae Windows. Si tu Windows está en español, lo normal es que solo tenga el OCR en español, que lee el inglés razonablemente bien pero confunde más letras.

Para mejorarlo: **Ajustes → Idioma del OCR → Instalar OCR en inglés…**. Pide permiso de administrador una vez y, cuando termine, la app empieza a usarlo sola. Equivale a ejecutar en PowerShell como administrador:

```powershell
Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
```

## Privacidad

- La lectura de pantalla (OCR) se hace **en tu PC**, sin internet. Las imágenes nunca se envían a ningún sitio.
- Solo el **texto reconocido** que no esté ya en la memoria local se envía a Google Translate (o a MyMemory si Google falla) para traducirlo.
- La memoria de traducciones, la configuración y el registro se guardan en `%APPDATA%\TraductorEnVivo\`. Puedes vaciar la memoria desde Ajustes.
- La comprobación de actualizaciones consulta la API pública de GitHub.

> Los servicios de traducción usados son gratuitos y no oficiales, o con límites diarios: el endpoint público de Google y la API anónima de MyMemory (unas 5000 palabras al día). Si alguno deja de funcionar, la app usa el otro, y la memoria local sigue funcionando siempre.

## Requisitos

- Windows 10 versión 1809 o posterior, o Windows 11, de 64 bits.
- Conexión a internet para traducir frases nuevas (opcional una vez que la memoria las tiene).

## Para desarrolladores

```powershell
git clone https://github.com/SoupOfMacaco/traductor-en-vivo
cd traductor-en-vivo
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
| `app/selector.py` | Selección de la zona con el ratón (multimonitor y DPI) |
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
- Varias zonas a la vez y perfiles por juego.
- Más servicios de traducción (DeepL con clave propia, LibreTranslate, modelos locales).
- Editar a mano las traducciones guardadas.

## Licencia

[MIT](LICENSE)
