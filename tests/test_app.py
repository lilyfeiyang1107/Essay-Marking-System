import copy
import io
import json
import unittest
from unittest.mock import patch

import httpx
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

import app as module


class EssayAppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(module.app)
        self.data = module.demo('narrative')
        self.submission = dict(genre='narrative', topic=self.data['topic'], essay=self.data['essay'])

    def test_home_and_assets(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertIn('上传记叙文', self.client.get('/').text)
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)

    def test_pwa_manifest_worker_and_public_assets(self):
        manifest = self.client.get('/static/manifest.webmanifest').json()
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(manifest['start_url'], '/')
        for icon in manifest['icons']:
            self.assertEqual(self.client.get(icon['src']).status_code, 200)
        worker = self.client.get('/sw.js')
        self.assertEqual(worker.status_code, 200)
        self.assertEqual(worker.headers['service-worker-allowed'], '/')
        self.assertEqual(worker.headers['cache-control'], 'no-cache')
        self.assertNotIn("'/api/review'", worker.text)
        self.assertNotIn("'/api/extract'", worker.text)
        for path in ['writing-garden.svg', 'story.svg', 'argument.svg']:
            self.assertEqual(self.client.get('/static/art/' + path).status_code, 200)

    def test_both_demos_are_complete_and_explicit(self):
        for genre in ['narrative', 'argumentative']:
            data = self.client.get('/api/demo/' + genre).json()
            r = data['report']
            self.assertTrue(r['demo'])
            self.assertEqual(r['total'], r['scores']['content'] + r['scores']['expression'])
            self.assertGreaterEqual(len(r['analysis']), 3)
            self.assertGreaterEqual(module.word_count(''.join(p['text'] for p in r['model_essay']['paragraphs'])), 500)
            self.assertTrue(all(p['note'] for p in r['model_essay']['paragraphs']))

    def test_text_upload_utf8_and_gb18030(self):
        for encoding in ['utf-8-sig', 'gb18030']:
            text = '那一次，我学会倾听。\n母亲站在伞下。'
            r = self.client.post('/api/extract', files={'file': ('作文.txt', text.encode(encoding), 'text/plain')})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['text'], text)

    def test_docx_upload_preserves_paragraphs(self):
        doc = Document()
        doc.add_paragraph('第一段：一个雨天。')
        doc.add_paragraph('第二段：我学会倾听。')
        b = io.BytesIO()
        doc.save(b)
        r = self.client.post('/api/extract', files={'file': ('作文.docx', b.getvalue())})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['text'], '第一段：一个雨天。\n第二段：我学会倾听。')

    def test_unsupported_corrupt_large_and_scanned_uploads(self):
        cases = [('essay.exe', b'bad', 415), ('essay.docx', b'broken', 422),
                 ('essay.txt', b'x' * (module.MAX_FILE + 1), 413)]
        writer = PdfWriter()
        writer.add_blank_page(width=600, height=800)
        b = io.BytesIO()
        writer.write(b)
        cases.append(('scanned.pdf', b.getvalue(), 422))
        for name, data, expected in cases:
            self.assertEqual(self.client.post('/api/extract', files={'file': (name, data)}).status_code, expected)

    def test_missing_ai_never_returns_fake_scores(self):
        with patch.dict(module.os.environ, {}, clear=True):
            self.assertFalse(self.client.get('/api/status').json()['ai_ready'])
            r = self.client.post('/api/review', json=self.submission)
            self.assertEqual(r.status_code, 503)
            self.assertNotIn('scores', r.json())

    def test_invalid_input_rejected(self):
        for updates in [dict(genre='other'), dict(topic=''), dict(essay='短文'), dict(essay='字'*20001)]:
            self.assertEqual(self.client.post('/api/review', json={**self.submission, **updates}).status_code, 422)

    def test_word_count_and_all_deduction_boundaries(self):
        self.assertEqual(module.word_count('华文，hello world 123！'), 5)
        for n, expected in [(399, 6), (400, 4), (449, 4), (450, 2), (490, 2), (491, None), (499, None), (500, 0)]:
            self.assertEqual(module.count_advice(n)['suggested'], expected)

    def test_reject_hallucinated_evidence_and_invalid_scores(self):
        sub = module.Submission(**self.submission)
        for field in ['correction', 'rewrite', 'score', 'analysis', 'model']:
            raw = copy.deepcopy(self.data['report'])
            if field == 'correction': raw['corrections'][0]['original'] = '不存在的原句'
            if field == 'rewrite': raw['rewrite']['original'] = '虚构的段落'
            if field == 'score': raw['scores']['content'] = 31
            if field == 'analysis': raw['analysis'][0]['evidence'] = '虚构的引文'
            if field == 'model': raw['model_essay']['paragraphs'] = [dict(text='很短', note='旁批')]*3
            with self.assertRaises(ValueError):
                module.validate_report(raw, sub)

    def test_live_review_contract_with_mock_provider(self):
        raw = self.data['report']
        observed = []
        def handler(request):
            observed.append(json.loads(request.content))
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(raw, ensure_ascii=False)}}]})
        original_client = httpx.AsyncClient
        def fake_client(**kwargs):
            return original_client(transport=httpx.MockTransport(handler))
        with patch.dict(module.os.environ, {'ESSAY_AI_KEY': 'test-key'}), patch.object(module.httpx, 'AsyncClient', fake_client):
            r = self.client.post('/api/review', json=self.submission)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['demo'])
        self.assertEqual(r.json()['total'], 45)
        self.assertEqual(observed[0]['response_format'], {'type': 'json_object'})
        self.assertIn('不可信', observed[0]['messages'][0]['content'])
        self.assertEqual(json.loads(observed[0]['messages'][1]['content'])['topic'], self.data['topic'])

    def test_provider_error_does_not_leak_body_or_secret(self):
        original_client = httpx.AsyncClient
        def fake_client(**kwargs):
            return original_client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text='private-provider-detail')))
        with patch.dict(module.os.environ, {'ESSAY_AI_KEY': 'test-secret'}), patch.object(module.httpx, 'AsyncClient', fake_client):
            r = self.client.post('/api/review', json=self.submission)
        self.assertEqual(r.status_code, 502)
        self.assertNotIn('private-provider-detail', r.text)
        self.assertNotIn('test-secret', r.text)


if __name__ == '__main__':
    unittest.main()
