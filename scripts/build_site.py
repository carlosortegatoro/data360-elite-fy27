"""Generate the static site from content/site.json, using only Python's stdlib."""
from __future__ import annotations

from datetime import date, time
from html import escape
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from string import Template
import sys
from urllib.parse import quote, unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def text(value, where, required=False):
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{where}: se espera un texto{' no vacío' if required else ''}.")
    return value


def obj(value, where):
    if not isinstance(value, dict):
        raise ValueError(f"{where}: se espera un objeto JSON.")
    return value


def array(value, where):
    if not isinstance(value, list):
        raise ValueError(f"{where}: se espera una lista JSON.")
    return value


def clock(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError(f"{where}: usa una hora HH:MM, por ejemplo 09:30.")
    try:
        return time.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{where}: la hora no es válida.") from error


def resource_url(resource, project, where):
    value = text(resource.get("url"), where + ".url", required=True)
    parsed = urlsplit(value)
    download = resource.get("download", False)
    if not isinstance(download, bool):
        raise ValueError(f"{where}.download: usa true o false.")
    if parsed.scheme == "https":
        if not parsed.hostname or parsed.username is not None or parsed.password is not None or any(c.isspace() for c in value):
            raise ValueError(f"{where}.url: usa una URL HTTPS completa, sin credenciales ni espacios.")
        if download:
            raise ValueError(f"{where}.download: la descarga directa se usa con ficheros en files/. Para servicios externos, usa false.")
        return value, None
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError(f"{where}.url: usa una URL HTTPS o una ruta relativa dentro de files/.")
    decoded = unquote(parsed.path)
    path = PurePosixPath(decoded)
    if "\\" in decoded or path.is_absolute() or not path.parts or path.parts[0] != "files" or any(part in ("..", ".") or part.startswith(".") for part in path.parts):
        raise ValueError(f"{where}.url: la ruta debe estar dentro de files/, sin directorios ocultos ni ../.")
    source = project.joinpath(*path.parts)
    if not source.resolve().is_relative_to((project / "files").resolve()) or source.is_symlink() or not source.is_file():
        raise ValueError(f"{where}.url: el fichero no existe en el repositorio: {decoded}.")
    return quote(path.as_posix(), safe="/"), path.as_posix()


def validate_resources(resources, project, where):
    for number, resource in enumerate(array(resources, where)):
        location = f"{where}[{number}]"
        obj(resource, location)
        text(resource.get("title"), location + ".title", required=True)
        for field in ("description", "button", "format"):
            text(resource.get(field, ""), location + "." + field)
        resource_url(resource, project, location)


def validate(data, project):
    obj(data, "site.json")
    program = obj(data.get("program"), "program")
    for field in ("name", "brand", "subtitle", "year", "timezone", "timezoneLabel"):
        text(program.get(field), "program." + field, required=True)
    for field in ("description", "footer", "featured"):
        text(program.get(field, ""), "program." + field)
    try:
        ZoneInfo(program["timezone"])
    except ZoneInfoNotFoundError as error:
        raise ValueError("program.timezone: la zona horaria no es válida.") from error
    seen = set()
    published = []
    for number, session in enumerate(array(data.get("sessions"), "sessions")):
        where = f"sessions[{number}]"
        obj(session, where)
        slug = text(session.get("slug"), where + ".slug", required=True)
        if not SLUG.fullmatch(slug) or slug == "index" or slug in seen:
            raise ValueError(f"{where}.slug: usa un identificador único en minúsculas y guiones, distinto de index.")
        seen.add(slug)
        text(session.get("title"), where + ".title", required=True)
        if not isinstance(session.get("published"), bool):
            raise ValueError(f"{where}.published: usa true o false.")
        if not session["published"]:
            continue
        value = session.get("date")
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(f"{where}.date: usa una fecha YYYY-MM-DD.")
        try:
            date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{where}.date: la fecha no es válida.") from error
        start, end = clock(session.get("start"), where + ".start"), clock(session.get("end"), where + ".end")
        if start >= end:
            raise ValueError(f"{where}: la hora de fin debe ser posterior al inicio.")
        for field in ("edition", "summary"):
            text(session.get(field, ""), where + "." + field)
        prework = obj(session.get("prework", {}), where + ".prework")
        for field in ("intro", "note"):
            text(prework.get(field, ""), where + ".prework." + field)
        for index, task in enumerate(array(prework.get("tasks", []), where + ".prework.tasks")):
            obj(task, where + f".prework.tasks[{index}]")
            text(task.get("title"), where + f".prework.tasks[{index}].title", required=True)
            text(task.get("description", ""), where + f".prework.tasks[{index}].description")
        validate_resources(prework.get("resources", []), project, where + ".prework.resources")
        validate_resources(session.get("materials", []), project, where + ".materials")
        agenda = obj(session.get("agenda", {}), where + ".agenda")
        text(agenda.get("note", ""), where + ".agenda.note")
        for index, item in enumerate(array(agenda.get("items", []), where + ".agenda.items")):
            location = where + f".agenda.items[{index}]"
            obj(item, location)
            text(item.get("title"), location + ".title", required=True)
            a, b = item.get("start"), item.get("end")
            if a is None and b is None:
                continue
            a, b = clock(a, location + ".start"), clock(b, location + ".end")
            if not start <= a < b <= end:
                raise ValueError(f"{location}: el bloque debe estar dentro del horario general de la cita.")
        published.append(session)
    featured = program.get("featured", "")
    if featured and featured not in {session["slug"] for session in published}:
        raise ValueError("program.featured: selecciona una cita publicada o deja el texto vacío.")
    return program, published


def e(value):
    return escape(str(value), quote=True)


def template(project, name, **values):
    return Template((project / "templates" / name).read_text(encoding="utf-8")).substitute(values)


def date_labels(session):
    day = date.fromisoformat(session["date"])
    short = f"{day.day} de {MONTHS[day.month]}"
    return day, short, f"{WEEKDAYS[day.weekday()]}, {short} de {day.year}"


def render_resource(resource, project, prework=False):
    url, local = resource_url(resource, project, resource["title"])
    download = resource.get("download", False)
    attributes = (' download="' + e(PurePosixPath(local).name) + '"') if download else (' target="_blank" rel="noopener noreferrer"' if local is None else '')
    button = resource.get("button") or ("Descargar fichero" if download else "Abrir recurso")
    arrow = "↓" if download else ("↗" if local is None else "→")
    metadata = f'<p class="elite-small">{e(resource["format"])}</p>' if resource.get("format") else ""
    link = f'<a class="elite-button elite-button-secondary" href="{e(url)}"{attributes}>{e(button)} <span aria-hidden="true">{arrow}</span></a>'
    title = f'<h3>{e(resource["title"])}</h3>'
    description = f'<p>{e(resource.get("description", ""))}</p>' if resource.get("description") else ""
    if prework:
        return f'<article class="elite-resource">{title}{description}{metadata}{link}</article>'
    return f'<article class="elite-materials"><div class="elite-materials-copy">{title}{description}{metadata}</div>{link}</article>'


def render_home(project, program, sessions):
    featured = next((item for item in sessions if item["slug"] == program.get("featured")), sessions[0] if sessions else None)
    cards = []
    for session in sessions:
        day, _, date_label = date_labels(session)
        cards.append(f'''<article class="elite-session">
<div class="elite-session-date" aria-hidden="true"><strong>{day.day}</strong><span>{MONTHS[day.month][:3].upper()} · {day.year}</span></div>
<div class="elite-session-copy"><p class="elite-eyebrow">{e(session.get('edition', ''))}</p><h3>{e(session['title'])}</h3><p>{e(session.get('summary', ''))}</p>
<div class="elite-topic-labels"><span>Pre-work</span><span>Agenda</span><span>Materiales</span></div>
<p class="elite-session-meta">{e(date_label)} · {e(session['start'])}–{e(session['end'])} · {e(program['timezoneLabel'])}</p></div>
<a class="elite-button elite-button-secondary" href="{session['slug']}.html" aria-label="Abrir la cita {e(session['title'])}">Abrir cita <span aria-hidden="true">→</span></a></article>''')
    featured_date = ""
    featured_button = '<a class="elite-button" href="#citas">Consultar citas</a>'
    if featured:
        day, _, _ = date_labels(featured)
        featured_button = f'<a class="elite-button" href="{featured["slug"]}.html">Abrir cita destacada <span aria-hidden="true">→</span></a>'
        featured_date = f'''<aside class="elite-date-card" aria-label="Cita destacada: {e(featured['title'])}"><p class="elite-eyebrow">Cita destacada</p><div class="elite-date-number">{day.day}</div><div class="elite-date-month">{MONTHS[day.month].capitalize()} {day.year}</div><div class="elite-date-time">{e(featured['start'])} — {e(featured['end'])}</div><span class="elite-small">{e(program['timezoneLabel'])} · {e(program['timezone'])}</span></aside>'''
    return template(project, "home.html", year=e(program["year"]), brand=e(program["brand"]), subtitle=e(program["subtitle"]), description=e(program.get("description", "")), featured_button=featured_button, featured_date=featured_date, sessions="\n".join(cards) or '<p>Las citas se publicarán aquí.</p>')


def render_session(project, program, session):
    _, short_date, date_label = date_labels(session)
    prework = session.get("prework", {})
    tasks = ''.join(f'<li><div><h3>{e(task["title"])}</h3><p>{e(task.get("description", ""))}</p></div></li>' for task in prework.get("tasks", []))
    resources = ''.join(render_resource(resource, project, prework=True) for resource in prework.get("resources", []))
    tasks = f'<ol class="elite-checklist">{tasks}</ol>' if tasks else ""
    resources = f'<div class="elite-prework-resources">{resources}</div>' if resources else ""
    if not tasks and not resources and not prework.get("intro"):
        tasks = '<p>El pre-work se publicará aquí.</p>'
    agenda = session.get("agenda", {})
    rows = []
    for index, item in enumerate(agenda.get("items", []), 1):
        label = f'{item["start"]}–{item["end"]}' if item.get("start") else "Por confirmar"
        rows.append(f'<tr><td>{index:02}</td><td>{e(item["title"])}</td><td>{e(label)}</td></tr>')
    table = f'<table class="elite-agenda"><caption class="elite-agenda-caption">{e(agenda.get("note", ""))}</caption><thead><tr><th scope="col">#</th><th scope="col">Bloque</th><th scope="col">Hora</th></tr></thead><tbody>{"".join(rows)}</tbody></table>' if rows else '<p>La agenda detallada se publicará aquí.</p>'
    materials = ''.join(render_resource(resource, project) for resource in session.get("materials", [])) or '<p>Los materiales se publicarán aquí.</p>'
    return template(project, "session.html", title=e(session["title"]), site_name=e(program["name"]), year=e(program["year"]), edition=f'<p class="elite-lead">{e(session["edition"])}</p>' if session.get("edition") else "", date_label=e(date_label), short_date=e(short_date), start=e(session["start"]), end=e(session["end"]), timezone_label=e(program["timezoneLabel"]), timezone=e(program["timezone"]), prework_intro=f'<p>{e(prework["intro"])}</p>' if prework.get("intro") else "", prework_note=f'<p class="elite-note">{e(prework["note"])}</p>' if prework.get("note") else "", prework_class="elite-work-grid" if tasks and resources else "elite-work-single", tasks=tasks, prework_resources=resources, agenda=table, materials=materials)


def build_site(project=ROOT, data=None):
    project = Path(project).resolve()
    if data is None:
        data = json.loads((project / "content" / "site.json").read_text(encoding="utf-8"))
    program, sessions = validate(data, project)
    bodies = [("index", render_home(project, program, sessions), program["name"])]
    bodies.extend((session["slug"], render_session(project, program, session), session["title"]) for session in sessions)
    pages = {}
    for slug, body, title in bodies:
        navigation = '<a href="index.html"' + (' aria-current="page"' if slug == "index" else '') + '>Inicio</a>'
        navigation += ''.join(f'<a href="{session["slug"]}.html"' + (' aria-current="page"' if slug == session["slug"] else '') + f'>{e(session["title"])}</a>' for session in sessions)
        pages[slug + ".html"] = template(project, "layout.html", page_title=e(f'{title} · {program["year"]}'), description=e(program.get("description", "")), site_name=e(program["name"]), brand=e(program["brand"]), subtitle=e(program["subtitle"]), year=e(program["year"]), navigation=navigation, body=body, footer=e(program.get("footer", "")))
    downloads = set()
    for session in sessions:
        resources = session.get("prework", {}).get("resources", []) + session.get("materials", [])
        for resource in resources:
            _, local = resource_url(resource, project, resource["title"])
            if local:
                downloads.add(local)
    assets = project / "assets"
    if not (assets / "styles.css").is_file() or assets.is_symlink() or any(path.is_symlink() for path in assets.rglob("*")):
        raise ValueError("assets/: faltan los estilos o hay enlaces simbólicos.")
    output = project / "dist"
    if output.is_symlink():
        raise ValueError("dist/ no puede ser un enlace simbólico.")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    for name, source in pages.items():
        (output / name).write_text(source, encoding="utf-8")
    shutil.copytree(assets, output / "assets", ignore=shutil.ignore_patterns(".*"))
    for relative in sorted(downloads):
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / relative, destination)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    return output


if __name__ == "__main__":
    try:
        destination = build_site()
    except (ValueError, OSError) as error:
        print(f"No se ha generado el microsite: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"Microsite generado en {destination}")
