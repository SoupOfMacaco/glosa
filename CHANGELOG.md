# Historial de cambios

Este proyecto usa [versionado semántico](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE`.

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
