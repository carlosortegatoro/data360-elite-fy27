from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

from scripts.build_site import ROOT, build_site


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids = []
        self.links = []
        self.anchors = []
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.tags.append((tag, attrs))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs["href"])
            self.anchors.append(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.links.append(attrs["href"])


class BuildSiteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)
        for name in ("templates", "assets"):
            shutil.copytree(ROOT / name, self.project / name)
        (self.project / "files").mkdir()
        self.data = json.loads((ROOT / "content/site.json").read_text())

    def build(self):
        return build_site(self.project, self.data)

    def material(self, url, **extra):
        item = {"title": "Recurso de prueba", "url": url, "download": False}
        item.update(extra)
        self.data["sessions"][0]["materials"].append(item)
        return item

    def test_existing_pages_keep_working_links_dates_and_resources(self):
        output = self.build()
        self.assertEqual({p.name for p in output.glob("*.html")}, {"index.html", "octubre-2026.html"})
        for name in ("index.html", "octubre-2026.html"):
            source = (output / name).read_text()
            self.assertIn("09:30", source)
            self.assertIn("14:00", source)
            self.assertIn("Jueves, 15 de octubre", source)
            page = Page(source)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            for link in page.links:
                parsed = urlsplit(link)
                if parsed.scheme:
                    self.assertEqual(parsed.scheme, "https")
                elif parsed.path:
                    self.assertTrue((output / unquote(parsed.path)).is_file(), link)
                else:
                    self.assertIn(parsed.fragment, page.ids)
        self.assertIn("docs.google.com/document/", (output / "octubre-2026.html").read_text())
        self.assertIn("docs.google.com/presentation/", (output / "octubre-2026.html").read_text())

    def test_new_published_session_creates_page_home_entry_and_navigation(self):
        session = deepcopy(self.data["sessions"][0])
        session.update(slug="cita-de-prueba", title="Cita de prueba", date="2027-01-12")
        self.data["sessions"].append(session)
        output = self.build()
        self.assertTrue((output / "cita-de-prueba.html").is_file())
        self.assertIn('href="cita-de-prueba.html"', (output / "index.html").read_text())
        self.assertIn('href="cita-de-prueba.html"', (output / "octubre-2026.html").read_text())

    def test_unfinished_draft_is_not_published(self):
        self.data["sessions"].append({"slug": "borrador", "title": "Borrador sin fecha", "published": False})
        output = self.build()
        self.assertFalse((output / "borrador.html").exists())
        self.assertNotIn("Borrador sin fecha", (output / "index.html").read_text())

    def test_local_download_is_copied_encoded_and_has_download_attribute(self):
        folder = self.project / "files/octubre-2026"
        folder.mkdir()
        (folder / "guía práctica.pdf").write_bytes(b"pdf-fixture")
        (folder / "sin-enlazar.txt").write_text("No publicar en el sitio")
        self.material("files/octubre-2026/guía práctica.pdf", download=True)
        output = self.build()
        self.assertEqual((output / "files/octubre-2026/guía práctica.pdf").read_bytes(), b"pdf-fixture")
        self.assertFalse((output / "files/octubre-2026/sin-enlazar.txt").exists())
        links = Page((output / "octubre-2026.html").read_text()).anchors
        download = next(link for link in links if "download" in link)
        self.assertEqual(download["download"], "guía práctica.pdf")
        self.assertEqual(download["href"], "files/octubre-2026/gu%C3%ADa%20pr%C3%A1ctica.pdf")

    def test_missing_file_does_not_destroy_previous_local_build(self):
        output = self.build()
        previous = (output / "index.html").read_bytes()
        self.material("files/ausente.pdf", download=True)
        with self.assertRaisesRegex(ValueError, "no existe"):
            self.build()
        self.assertEqual(previous, (output / "index.html").read_bytes())

    def test_invalid_url_schemes_and_credentials_are_rejected(self):
        for url in ("javascript:alert(1)", "data:text/html,test", "http://example.com/", "//example.com/", "https://user:password@example.com/"):
            with self.subTest(url=url):
                item = self.material(url)
                with self.assertRaises(ValueError):
                    self.build()
                self.data["sessions"][0]["materials"].remove(item)

    def test_download_cannot_escape_files_directory(self):
        (self.project / "outside.txt").write_text("Fixture")
        (self.project / "files/link.txt").symlink_to(self.project / "outside.txt")
        for url in ("files/../outside.txt", "files/%2e%2e/outside.txt", "/files/outside.txt", "files/.env", "files/link.txt"):
            with self.subTest(url=url):
                item = self.material(url)
                with self.assertRaises(ValueError):
                    self.build()
                self.data["sessions"][0]["materials"].remove(item)

    def test_external_resources_open_separately_and_do_not_claim_forced_download(self):
        item = self.material("https://example.com/recurso?x=1&y=2")
        output = self.build()
        links = Page((output / "octubre-2026.html").read_text()).anchors
        link = next(link for link in links if link["href"] == item["url"])
        self.assertEqual(link["target"], "_blank")
        self.assertIn("noopener", link["rel"])
        self.assertNotIn("download", link)
        item["download"] = True
        with self.assertRaisesRegex(ValueError, "descarga directa"):
            self.build()

    def test_agenda_times_must_fit_session_window(self):
        item = self.data["sessions"][0]["agenda"]["items"][0]
        item.update(start="09:30", end="10:00")
        self.assertIn("09:30–10:00", (self.build() / "octubre-2026.html").read_text())
        item.update(start="09:00", end="10:00")
        with self.assertRaisesRegex(ValueError, "horario general"):
            self.build()
        item.update(start="09:30", end=None)
        with self.assertRaises(ValueError):
            self.build()

    def test_content_is_escaped_as_text(self):
        self.data["sessions"][0]["title"] = '<script>alert("x")</script>'
        self.material("https://example.com/", title='<img src=x onerror="alert(1)">')
        output = self.build()
        source = (output / "octubre-2026.html").read_text()
        self.assertIn("&lt;script&gt;", source)
        self.assertIn("&lt;img", source)
        self.assertFalse(any(tag in ("script", "img") for tag, _ in Page(source).tags))

    def test_duplicate_and_reserved_slugs_are_rejected(self):
        self.data["sessions"].append(deepcopy(self.data["sessions"][0]))
        with self.assertRaisesRegex(ValueError, "identificador único"):
            self.build()
        self.data["sessions"].pop()
        self.data["sessions"][0]["slug"] = "index"
        with self.assertRaises(ValueError):
            self.build()

    def test_unpublishing_removes_old_page_from_next_artifact(self):
        output = self.build()
        self.assertTrue((output / "octubre-2026.html").is_file())
        self.data["sessions"][0]["published"] = False
        self.data["program"]["featured"] = ""
        output = self.build()
        self.assertFalse((output / "octubre-2026.html").exists())
        self.assertNotIn('href="octubre-2026.html"', (output / "index.html").read_text())


if __name__ == "__main__":
    unittest.main()
