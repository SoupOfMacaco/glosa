# Historial de cambios

Este proyecto usa [versionado semántico](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE`.

## [1.3.0] - 2026-11-20

- **Transparencia del texto flotante**: nuevo control "Opacidad del texto" (20-100 %) en Ajustes.
- La "Opacidad del fondo" ahora llega hasta 0 %, es decir, sin fondo. Con poco fondo, el texto lleva un contorno oscuro para que se siga leyendo.
- **Licencia**: el proyecto pasa de MIT a **PolyForm Noncommercial 1.0.0**. Se permite el uso personal y no comercial y no se permite ningún uso comercial. El instalador muestra la licencia y hay que aceptarla.
- **Vista previa en vivo**: al mover los controles de opacidad o tamaño de letra, la traducción en pantalla cambia al momento. Si no hay ninguna traducción, aparece un texto de ejemplo. Al pulsar Cancelar, todo vuelve como estaba.

## [1.2.0] - 2026-11-20

- **Varias zonas a la vez**: el editor de zonas (`Ctrl+Shift+T`) permite marcar varias, por ejemplo diálogos arriba y abajo. Cada zona tiene su propio lector y su traducción flotante, y en la esquina se apilan como "Zona 1", "Zona 2"...
- **Perfiles**: las zonas se guardan en perfiles. Al marcarlas desde un juego, el perfil queda vinculado a ese juego y se activa solo al volver a jugarlo. Menú **Perfiles** en la bandeja y atajo `Ctrl+Shift+O` para cambiar de perfil.
- Ya no traduce texto que ya está en español, como ventanas de Windows u otros programas en la zona.
- Ignora las líneas basura que el OCR saca de bordes y adornos.
- La zona que tenías en versiones anteriores se conserva en el perfil "General".

## [1.1.0] - 2026-11-20

- La app pasa a llamarse **Glosa** y estrena logo.
- El instalador ofrece instalar el OCR en inglés de Windows, con la casilla marcada por defecto, para que al abrir la app ya esté todo listo. Sigue disponible también en Ajustes.
- Al actualizar desde la 1.0.0 se conservan la memoria de traducciones, los ajustes y el inicio con Windows, y se borran los accesos directos antiguos.

## [1.0.0] - 2026-11-20

Primera versión.

- Lectura en vivo de una zona de la pantalla con el OCR de Windows 10/11.
- Detecta cuándo cambia el texto y espera a que termine de escribirse antes de traducir.
- Traducción híbrida: memoria local que crece sola, glosario de frases de juegos y traducción online gratuita (Google, con MyMemory como respaldo).
- Dos formas de mostrar la traducción: flotante sobre el texto (tapándolo o justo encima) y en una esquina, o las dos a la vez.
- Las ventanas de traducción no salen en capturas de pantalla, así que el OCR nunca lee su propia traducción.
- Corrección de errores típicos del OCR con fuentes pixeladas.
- Icono en la bandeja del sistema, atajos de teclado globales y ventana de ajustes.
- Instalador sin permisos de administrador y actualizaciones automáticas desde GitHub Releases.
