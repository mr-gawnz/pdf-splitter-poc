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

## Ubuntu / DigitalOcean deployment

These instructions assume the repository is checked out at `/opt/pdf-splitter-poc`, and use Nginx in front of a loopback-only Uvicorn service. Deploy the code there as your normal deployment user, with read and directory traversal access for `www-data`.

```bash
sudo apt update
sudo apt install -y python3-venv nginx
cd /opt/pdf-splitter-poc
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
sudo -u www-data .venv/bin/python -c 'from app import app; print(app.title)'
sudo cp deploy/pdf-splitter.service /etc/systemd/system/pdf-splitter.service
sudo systemctl daemon-reload
sudo systemctl enable --now pdf-splitter
curl --fail http://127.0.0.1:8000/health
```

Replace `YOUR_DOMAIN` in `deploy/nginx.conf` with your domain (or server IP), then install and validate it:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/pdf-splitter
sudo ln -s /etc/nginx/sites-available/pdf-splitter /etc/nginx/sites-enabled/pdf-splitter
sudo nginx -t
sudo systemctl reload nginx
```

Allow HTTP/HTTPS through your DigitalOcean firewall and enable HTTPS for your domain, for example with Certbot's Nginx integration. Port 8000 stays private. Use `journalctl -u pdf-splitter -e` for application logs. After updating the code or dependencies, run `sudo systemctl restart pdf-splitter`.

The application has no authentication. Add access control at Nginx if you want a private tool. The 50 MiB limit constrains input size, not PDF complexity or output size; size the server for your PDFs before exposing it to heavy traffic. Nginx limits the request body to 52 MiB including multipart overhead. Real PDF compatibility checks below remain necessary.

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
