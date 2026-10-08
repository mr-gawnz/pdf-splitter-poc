from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import pikepdf

from app import app
from smoke_test import make_test_pdf


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def upload(self, data=None, **options):
        return self.client.post(
            '/api/split',
            files={'file': ('spread.pdf', make_test_pdf() if data is None else data, 'application/pdf')},
            data=options,
        )

    def test_health_and_ui(self):
        self.assertEqual(self.client.get('/health').json(), {'status': 'ok'})
        self.assertIn('id="split-form"', self.client.get('/').text)
        for path in ('/static/app.js', '/static/styles.css'):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_subpath_ui_assets_api_and_docs(self):
        client = TestClient(app, root_path='/splitter', base_url='https://middleware.ipaperdemo.io')
        response = client.get('/splitter/')
        self.assertEqual(response.status_code, 200)

        class AssetParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.urls = []

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == 'link':
                    self.urls.append(attributes['href'])
                elif tag == 'script':
                    self.urls.append(attributes['src'])

        parser = AssetParser()
        parser.feed(response.text)
        self.assertEqual(len(parser.urls), 2)
        for asset in parser.urls:
            url = urljoin(str(response.url), asset)
            self.assertIn('/splitter/static/', url)
            self.assertEqual(client.get(url).status_code, 200)

        script = client.get('/splitter/static/app.js').text
        self.assertIn("fetch('api/split'", script)
        api_url = urljoin(str(response.url), 'api/split')
        result = client.post(api_url, files={'file': ('spread.pdf', make_test_pdf(), 'application/pdf')})
        self.assertEqual(result.status_code, 200)
        with pikepdf.Pdf.open(BytesIO(result.content)) as pdf:
            self.assertEqual(len(pdf.pages), 2)
        self.assertEqual(client.get('/splitter/health').json(), {'status': 'ok'})
        self.assertIn('/splitter/openapi.json', client.get('/splitter/docs').text)
        schema = client.get('/splitter/openapi.json').json()
        self.assertIn({'url': '/splitter'}, schema['servers'])

    def test_default_split_and_download(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/pdf')
        self.assertIn('spread_split.pdf', response.headers['content-disposition'])
        self.assertEqual(response.headers['x-input-pages'], '1')
        self.assertEqual(response.headers['x-split-pages'], '1')
        self.assertEqual(response.headers['x-untouched-pages'], '0')
        with pikepdf.Pdf.open(BytesIO(response.content)) as pdf:
            self.assertEqual(len(pdf.pages), 2)
            self.assertEqual(list(pdf.pages[0].cropbox), [0, 0, 500, 600])
            self.assertEqual(list(pdf.pages[1].cropbox), [500, 0, 1000, 600])
            self.assertTrue(all('/Annots' in page.obj for page in pdf.pages))

    def test_reverse_order(self):
        response = self.upload(order='right-left')
        self.assertEqual(response.status_code, 200)
        with pikepdf.Pdf.open(BytesIO(response.content)) as pdf:
            self.assertEqual(list(pdf.pages[0].cropbox), [500, 0, 1000, 600])
            self.assertEqual(list(pdf.pages[1].cropbox), [0, 0, 500, 600])

    def test_portrait_filter_and_override(self):
        source = BytesIO()
        with pikepdf.Pdf.new() as pdf:
            pdf.add_blank_page(page_size=(600, 1000))
            pdf.save(source)
        response = self.upload(source.getvalue())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['x-untouched-pages'], '1')
        with pikepdf.Pdf.open(BytesIO(response.content)) as pdf:
            self.assertEqual(len(pdf.pages), 1)
        response = self.upload(source.getvalue(), only_landscape='false')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['x-split-pages'], '1')
        with pikepdf.Pdf.open(BytesIO(response.content)) as pdf:
            self.assertEqual(len(pdf.pages), 2)
            self.assertEqual(list(pdf.pages[0].cropbox), [0, 0, 300, 1000])

    def test_empty_upload(self):
        self.assertEqual(self.upload(b'').status_code, 400)

    def test_invalid_pdf(self):
        response = self.upload(b'not a PDF')
        self.assertEqual(response.status_code, 422)
        self.assertIn('valid PDF', response.json()['detail'])

    def test_encrypted_pdf(self):
        source = BytesIO()
        with pikepdf.Pdf.open(BytesIO(make_test_pdf())) as pdf:
            pdf.save(source, encryption=pikepdf.Encryption(owner='owner', user='password', R=6))
        self.assertEqual(self.upload(source.getvalue()).status_code, 400)

    def test_oversized_upload(self):
        with patch('app.MAX_UPLOAD_BYTES', 10):
            self.assertEqual(self.upload(b'x' * 11).status_code, 413)

    def test_invalid_options_and_missing_file(self):
        self.assertEqual(self.upload(order='invalid').status_code, 422)
        self.assertEqual(self.upload(only_landscape='invalid').status_code, 422)
        self.assertEqual(self.client.post('/api/split').status_code, 422)

    def test_unicode_download_filename(self):
        response = self.client.post('/api/split', files={
            'file': ('../prøve.pdf', make_test_pdf(), 'application/octet-stream'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("filename*=UTF-8''pr%C3%B8ve_split.pdf", response.headers['content-disposition'])


if __name__ == '__main__':
    unittest.main()
