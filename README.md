# PDF Half Splitter POC

A FastAPI web app and API that split landscape PDF spreads vertically without rasterization. The UI is plain HTML, CSS and JavaScript, so you can customize it independently of the PDF logic.

## Why this approach

The splitter duplicates each eligible PDF page **inside the same document** and changes its page boxes so that one copy exposes the left half and the other exposes the right half.

It does **not** render the page to an image and rebuild it. This gives us a much better chance of preserving:

- vector content
- selectable text and embedded fonts
- URL/link annotations
- Optional Content Groups (PDF layers)
- transparency and other page resources

This is intentionally a POC. The first thing to validate with real iPaper/customer PDFs is whether links, OCG layers and unusual page rotations behave correctly in Adobe Acrobat and the iPaper import pipeline.

## Develop locally (Python 3.10+)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the UI, or `/docs` for the interactive API documentation. On Windows, create the environment with `py -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1`.

- `app.py`: FastAPI routes, upload validation and PDF downloads.
- `splitter.py`: existing PDF logic.
- `static/index.html`, `static/styles.css`, `static/app.js`: customizable UI; no frontend build required.

Run the checks:

```bash
python smoke_test.py
python -m unittest -v test_api
```

The app is tested with Python 3.10 and 3.12. The PikePDF requirement allows 10.13, which supports Python 3.10; newer PikePDF releases may require Python 3.11+. Pip selects a compatible release.

ReportLab and HTTPX are test dependencies in `requirements-dev.txt`; production only needs `requirements.txt`.

## API

`POST /api/split` accepts multipart form fields:

| Field | Default | Description |
| --- | --- | --- |
| `file` | Required | PDF file, up to 50 MiB |
| `only_landscape` | `true` | Set `false` to split every page |
| `order` | `left-right` | `left-right` or `right-left` |

Success returns PDF bytes with an attachment filename and `X-Input-Pages`, `X-Split-Pages` and `X-Untouched-Pages` headers. Empty or password-protected PDFs return HTTP 400, oversized uploads return 413, and malformed PDFs or invalid form options return 422. Files are processed for the response and are not saved by application code; multipart uploads may use temporary files managed by the framework.

```bash
curl --fail-with-body -X POST http://127.0.0.1:8000/api/split \
  -F 'file=@spread.pdf' \
  -F 'only_landscape=true' \
  -F 'order=left-right' \
  --output spread_split.pdf
```

`GET /health` returns `{"status":"ok"}`.

## Apache / DigitalOcean deployment

The production URL is **https://middleware.ipaperdemo.io/splitter/**. Apache redirects `/splitter` to `/splitter/` so relative UI URLs resolve correctly. Uvicorn runs privately on `127.0.0.1:8001` under systemd, which starts it on boot and restarts it if it exits. The existing middleware and HTTPS virtual host stay in place.

The service file assumes this checkout lives at `/var/www/html/splitter`. Python 3.10+ and `python3-venv` are required. From the droplet:

```bash
cd /var/www/html/splitter
git pull --ff-only origin main
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
sudo -u www-data .venv/bin/python -c 'from app import app; print(app.title)'
sudo cp deploy/pdf-splitter.service /etc/systemd/system/pdf-splitter.service
sudo systemctl daemon-reload
sudo systemctl enable pdf-splitter
sudo systemctl restart pdf-splitter
sudo systemctl status pdf-splitter --no-pager
curl --fail http://127.0.0.1:8001/health
```

Ensure `www-data` can read the project and virtual environment and traverse their parent directories. If port 8001 is already used, choose a free port in both the systemd service and Apache proxy configuration. The service uses `--root-path /splitter`, keeping API docs and generated URLs under the public prefix. The UI uses relative URLs and also works at `/` during local development.

Enable the required Apache modules and install the proxy snippet:

```bash
sudo a2enmod proxy proxy_http headers alias
sudo cp deploy/apache-splitter.conf /etc/apache2/splitter-proxy.conf
sudo apache2ctl -S
```

Use the last command to identify the **existing HTTPS virtual host for middleware.ipaperdemo.io**. Add this line **inside its `<VirtualHost ...:443>` block**, before any catch-all proxy rules:

```apache
Include /etc/apache2/splitter-proxy.conf
```

The snippet is intended for that HTTPS virtual host, not a global `a2enconf` include. It proxies only `/splitter/` and denies direct filesystem access to the checkout, including `.git` and `.venv`. Do not add a second virtual host or replace the existing middleware configuration.

Validate and reload Apache:

```bash
sudo apache2ctl configtest
sudo systemctl reload apache2
curl --fail https://middleware.ipaperdemo.io/splitter/health
```

The health response should be `{"status":"ok"}`. Open the public URL and upload a PDF to check the entire workflow. Interactive API docs are at `/splitter/docs`. Apache owns the HTTPS certificate; port 8001 does not need public firewall access.

For logs:

```bash
sudo journalctl -u pdf-splitter -n 100 --no-pager
sudo tail -n 100 /var/log/apache2/error.log
```

After future code updates:

```bash
cd /var/www/html/splitter
git pull --ff-only origin main
.venv/bin/python -m pip install -r requirements.txt
sudo systemctl restart pdf-splitter
```

The app has no authentication. Apply your existing Apache access controls to `/splitter/` if this is a private tool. Apache caps uploads at 52 MiB including multipart overhead; the application caps the PDF itself at 50 MiB. PDF complexity and output size can still affect resource use. Real PDF compatibility checks below remain necessary.

## Recommended first test

Use a landscape/spread PDF that contains:

- at least one hyperlink on each half
- a visible and hidden PDF layer
- vector text/artwork

After splitting, inspect the result in Acrobat:

1. Confirm there are now two half-width pages for each original spread.
2. Click links on both halves.
3. Open the Layers panel and toggle the original layers.
4. Zoom in heavily to confirm vector/text content was not rasterized.

## Current POC limitations

- The cut is always exactly 50/50 vertically.
- It assumes landscape pages are spreads when `Split only landscape pages` is enabled.
- Rotated/cropped PDFs need real-world testing.
- An annotation that crosses the centre line is currently present on both page copies; its visible portion is naturally clipped by the page box, but we are not yet rewriting annotation rectangles.
- Internal page links/bookmarks that target specific page objects need dedicated regression tests when a source page is duplicated.
- Interactive AcroForm PDFs are not a target of this first POC.

## Next step if the preservation test succeeds

Add annotation-aware processing so each output half gets only annotations intersecting that half, with centre-crossing link rectangles clipped to the visible half. Then add page-rotation handling and automated structural regression tests.
