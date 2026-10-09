# Data360 Elite Program FY27

[Abrir el microsite](https://carlosortegatoro.github.io/data360-elite-fy27/)

La home y las páginas de las citas se generan desde **[content/site.json](content/site.json)**.
Para cambiar textos, horarios o recursos no necesitas editar HTML ni instalar nada:
puedes modificar ese archivo desde GitHub. Quien edite necesita acceso de escritura
al repositorio.

La cita de octubre mantiene el 15 de octubre de 2026, de 09:30 a 14:00, hora de Madrid.
La home ofrece acceso directo a la guía PDF y al ZIP de materiales, muestra la agenda
y permite leer el PDF con **Leer el pre-work aquí**, sin abrir otra página de la cita.
Las horas de los bloques están pendientes de confirmar.

El botón **Pre-work** utiliza el primer recurso de `prework.resources`, y
**Materiales** el primero de `materials`. Los recursos adicionales también se muestran
en la home. Coloca primero el documento o fichero que quieras destacar.

## Añadir un enlace externo

1. Abre `content/site.json` y pulsa el lápiz de edición en GitHub.
2. Localiza la cita dentro de `sessions`.
3. Añade un objeto a `materials` o a `prework.resources`, separado del anterior por una coma:

```json
{
  "title": "Nombre del documento",
  "description": "Qué encontrará el asistente en este recurso.",
  "url": "https://example.com/documento",
  "button": "Abrir documento",
  "format": "PDF",
  "download": false
}
```

4. Sustituye la URL por el enlace real de Drive, SharePoint, una presentación,
   un vídeo u otro servicio. Usa enlaces HTTPS.
5. Guarda con **Commit changes** en `main`.

Los recursos externos se abren en otra pestaña y mantienen los permisos de su
proveedor. Para acceso sin iniciar sesión, el recurso debe permitir acceso público
o mediante enlace. Publicar el microsite no concede acceso a los documentos de Drive.
La guía PDF y el ZIP se alojan directamente en el microsite.

## Añadir un fichero descargable

1. Desde GitHub, abre **[files/](files/)** y usa **Add file → Upload files** para subirlo.
   Puedes crear subcarpetas por cita. Guarda primero la subida en `main`.
2. Añade el recurso a la cita en `content/site.json`:

```json
{
  "title": "Guía de la sesión",
  "description": "Documento de preparación para los asistentes.",
  "url": "files/guia-sesion.pdf",
  "button": "Descargar guía",
  "format": "PDF",
  "download": true
}
```

3. Usa la ruta y el nombre exactos del fichero, respetando mayúsculas y minúsculas.
   Si lo guardas en una subcarpeta, por ejemplo `files/octubre-2026/`, incluye esa
   carpeta en `url`.
4. Guarda el contenido en `main` y espera la publicación.

Puedes usar PDF, PowerPoint, Word, Excel, ZIP, imágenes u otros formatos. La web
ofrece el enlace o la descarga; la visualización depende del navegador y del formato.
`download: true` está previsto para archivos en `files/`. En un enlace externo usa
`download: false`, porque la descarga la controla ese servicio.

El repositorio es público. Los archivos referenciados de `files/` se copian al
microsite y se pueden abrir sin cuenta de GitHub. Los archivos subidos pero todavía
sin referencia no se copian al sitio, aunque siguen siendo visibles en el repositorio.

## Mostrar una guía PDF dentro del microsite

En un recurso de `prework.resources`, usa una ruta local a un PDF, `download: false`
y `embed: true`:

```json
{
  "title": "Guía de pre-work",
  "url": "files/octubre-2026/Guia_Prework_SOMA_2026.pdf",
  "button": "Abrir guía PDF",
  "format": "PDF",
  "download": false,
  "embed": true
}
```

La guía se enlaza directamente y aparece una vista integrada desplegable en la home
y en la página de la cita. Incluye un enlace alternativo para navegadores que no
visualizan PDFs integrados. Usa `embed: false` u omítelo para recursos sin visor.

## Añadir una nueva cita

1. Copia el objeto de **[content/session.example.json](content/session.example.json)**
   y añádelo a la lista `sessions` de `content/site.json`. Ese archivo de ejemplo
   por sí solo no crea ninguna página.
2. Usa un `slug` único, en minúsculas y con guiones; por ejemplo, el nombre de la
   cita. Ese identificador determina la URL `slug.html`.
3. Completa `title`, `date` (`YYYY-MM-DD`), `start` y `end` (`HH:MM`).
4. Añade los textos de `prework`, los bloques de `agenda.items` y los `materials`.
5. Cambia `published` a `true` cuando la cita esté preparada.

La página y su entrada con recursos y agenda en la home se generan automáticamente.
Las citas con `published: false` se mantienen como borrador y no aparecen en la web.
Para retirar una cita destacada, cambia también `program.featured` a otra cita
publicada o a `""`. El orden de las citas es el de la lista `sessions`.

## Cambiar la cita destacada y el programa

En `program` puedes cambiar el nombre, los textos de la home, el año fiscal, el pie,
la zona horaria y `featured`. Este último campo contiene el `slug` de la cita destacada.
La zona horaria común se configura con `timezone` y `timezoneLabel`.

## Completar el horario de cada bloque

En cada elemento de `agenda.items`, sustituye ambos valores `null` por horas:

```json
{ "title": "Bienvenida", "start": "09:30", "end": "10:00" }
```

Mantén ambos en `null` cuando estén pendientes. Los bloques deben estar dentro del
horario general de la cita y su fin debe ser posterior al inicio.

## Publicación y comprobaciones

Cada cambio en `main` ejecuta **[Publicar microsite](https://github.com/carlosortegatoro/data360-elite-fy27/actions)**:
comprueba el contenido, genera las páginas y publica `dist/` en GitHub Pages.
Las propuestas mediante pull request se comprueban sin publicarse.

Si hay JSON incorrecto, una fecha inválida, un identificador repetido o un fichero
local que falta, la publicación se detiene y la última versión publicada permanece
disponible. Consulta el error en **Actions → Publicar microsite → build**.
No se comprueba automáticamente el acceso a los recursos externos: prueba sus
enlaces con un asistente externo antes de distribuirlos.

Las páginas incluyen `noindex, nofollow` para pedir que no se indexen; siguen siendo
públicas y el enlace se puede reenviar. Las actualizaciones se realizan en GitHub.

## Desarrollo local

Python 3.11 o posterior, sin dependencias adicionales:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
```

El resultado está en `dist/`. Los estilos se editan en `assets/styles.css`, la
estructura en `templates/` y el generador en `scripts/build_site.py`.
No edites los archivos generados de `dist/`: se vuelven a crear en cada publicación.

El logo de Salesforce se incluye como `assets/salesforce-logo.jpg`, obtenido de la
[biblioteca oficial de Salesforce](https://www.salesforce.com/news/media-library/).

El flujo de publicación sigue la [documentación oficial de GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
