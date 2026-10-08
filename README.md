# Data360 Elite Program FY27

Microsite estático para las citas del programa. La home enlaza a la primera cita,
el 15 de octubre de 2026, de 09:30 a 14:00, hora de Madrid.

## Páginas

- `index.html`: home y directorio de citas.
- `octubre-2026.html`: pre-work, horario, agenda y materiales de octubre.
- `assets/styles.css`: diseño compartido y adaptable a móvil.

El pre-work está marcado como propuesta basada en la guía práctica del programa.
Las horas de los bloques de agenda están pendientes de confirmar; el horario
general sí está confirmado.

## Publicación

GitHub Pages publica la rama `main` desde `/ (root)`. El archivo `.nojekyll`
permite servir directamente HTML y CSS, sin dependencias ni compilación.
Los cambios publicados en `main` actualizan el microsite automáticamente.

El microsite es público y se puede visitar sin cuenta de GitHub. Los enlaces
a Google Drive conservan los permisos de los documentos originales. Publicar
el microsite no concede acceso a esos documentos. Comprueba ambos enlaces
con un asistente externo antes de distribuirlos.

Las páginas incluyen `noindex, nofollow` para pedir a los buscadores que no
las indexen. Esto no restringe el acceso ni impide que se reenvíe el enlace.

## Añadir otra cita

1. Copia `octubre-2026.html` con un nombre descriptivo para la nueva cita.
2. Cambia el título, la fecha, el horario, el pre-work y los recursos.
3. Actualiza los enlaces de navegación y añade una entrada en `index.html`.
4. Comprueba la navegación entre las páginas y los permisos de los recursos.
5. Publica los cambios en `main`.
