from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote

import pikepdf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from splitter import split_pdf_bytes

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

app = FastAPI(title="PDF Half Splitter", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/split", response_class=Response, responses={
    200: {"content": {"application/pdf": {}}},
    400: {"description": "Empty or password-protected PDF"},
    413: {"description": "PDF exceeds 200 MiB"},
    422: {"description": "Invalid PDF or form options"},
})
def split_pdf(
    file: Annotated[UploadFile, File(description="PDF to split")],
    only_landscape: Annotated[bool, Form()] = True,
    order: Annotated[Literal["left-right", "right-left"], Form()] = "left-right",
) -> Response:
    # A synchronous endpoint runs in FastAPI's thread pool, keeping PDF work
    # and file reads off the event loop. Do not trust the client MIME type.
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Choose a non-empty PDF.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF must be 200 MiB or smaller.")

    try:
        result, stats = split_pdf_bytes(data, only_landscape=only_landscape, order=order)
    except pikepdf.PasswordError as exc:
        raise HTTPException(status_code=400, detail="Password-protected PDFs are not supported.") from exc
    except pikepdf.PdfError as exc:
        raise HTTPException(status_code=422, detail="Could not read this PDF. Check that it is a valid PDF.") from exc

    # Strip paths and control characters before constructing the download header.
    name = (file.filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
    base = name.rsplit(".", 1)[0] if "." in name else name
    base = "".join(c for c in base if c.isprintable()).strip()[:150] or "document"
    filename = quote(f"{base}_split.pdf", safe="")
    return Response(
        content=result,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"document_split.pdf\"; filename*=UTF-8''{filename}",
            "X-Input-Pages": str(stats.input_pages),
            "X-Split-Pages": str(stats.split_pages),
            "X-Untouched-Pages": str(stats.untouched_pages),
            "Cache-Control": "no-store",
        },
    )
