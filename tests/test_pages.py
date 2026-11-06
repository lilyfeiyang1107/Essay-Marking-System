import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
from scripts.build_pages import build


class PagesPublicationTests(unittest.TestCase):
    def test_project_path_icons_demos_worker_and_no_private_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            build(output)
            html = (output / 'index.html').read_text()
            self.assertIn('/Essay-Marking-System/static/app.js', html)
            self.assertNotIn('src="/static/', html)
            manifest = json.loads((output / 'static/manifest.webmanifest').read_text())
            self.assertEqual(manifest['start_url'], '/Essay-Marking-System/')
            self.assertEqual(manifest['scope'], '/Essay-Marking-System/')
            self.assertTrue(all(i['src'].startswith('/Essay-Marking-System/') for i in manifest['icons']))
            config = (output / 'static/site-config.js').read_text()
            self.assertIn('"apiBase": ""', config)
            self.assertNotIn('ESSAY_AI_KEY', config)
            self.assertFalse((output / 'app.py').exists())
            self.assertFalse((output / '.env').exists())
            self.assertTrue((output / '.nojekyll').exists())
            for genre in ['narrative', 'argumentative']:
                data = json.loads((output / 'examples' / f'{genre}.json').read_text())
                self.assertTrue(data['report']['demo'])
                self.assertEqual(data['report']['total'], data['report']['scores']['content'] + data['report']['scores']['expression'])
            worker = (output / 'sw.js').read_text()
            self.assertIn('/Essay-Marking-System/examples/narrative.json', worker)
            self.assertNotIn('/api/demo/', worker)
            self.assertNotIn('/api/review', worker)
            js = (output / 'static/mobile-app.js').read_text()
            self.assertIn("register('/Essay-Marking-System/sw.js')", js)

    def test_valid_backend_is_public_url_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp, '/test/', 'https://example.onrender.com/')
            self.assertIn('https://example.onrender.com', (Path(tmp) / 'static/site-config.js').read_text())
            for value in ['http://example.com', 'https://key@example.com', 'https://example.com?api_key=secret', 'https://example.com/api']:
                with self.assertRaises(ValueError):
                    build(tmp, '/test/', value)

    def test_cors_allows_only_configured_pages_origin(self):
        try:
            with patch.dict(os.environ, {'WENMO_ALLOWED_ORIGINS': 'https://lilyfeiyang1107.github.io'}):
                configured = importlib.reload(app).app
                client = TestClient(configured)
                allowed = client.options('/api/review', headers={
                    'Origin':'https://lilyfeiyang1107.github.io',
                    'Access-Control-Request-Method':'POST',
                    'Access-Control-Request-Headers':'content-type'})
                self.assertEqual(allowed.status_code, 200)
                self.assertEqual(allowed.headers['access-control-allow-origin'], 'https://lilyfeiyang1107.github.io')
                denied = client.options('/api/review', headers={
                    'Origin':'https://other.example', 'Access-Control-Request-Method':'POST'})
                self.assertEqual(denied.status_code, 400)
                self.assertNotIn('access-control-allow-origin', denied.headers)
        finally:
            importlib.reload(app)
