from io import BytesIO

import pikepdf
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, blue

from splitter import split_pdf_bytes


def make_test_pdf() -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(1000, 600))
    c.setFillColor(red)
    c.rect(0, 0, 500, 600, fill=1, stroke=0)
    c.setFillColor(blue)
    c.rect(500, 0, 500, 600, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 24)
    c.drawString(100, 300, "LEFT")
    c.drawString(650, 300, "RIGHT")
    c.linkURL("https://example.com/left", (80, 260, 250, 330), relative=0)
    c.linkURL("https://example.com/right", (630, 260, 840, 330), relative=0)
    c.showPage()
    c.save()
    return buf.getvalue()


def main() -> None:
    source = make_test_pdf()
    result, stats = split_pdf_bytes(source)

    with pikepdf.Pdf.open(BytesIO(result)) as pdf:
        assert len(pdf.pages) == 2
        widths = [float(p.cropbox[2]) - float(p.cropbox[0]) for p in pdf.pages]
        assert widths == [500.0, 500.0]
        assert all("/Annots" in p.obj for p in pdf.pages)

    print("Smoke test passed:", stats)


if __name__ == "__main__":
    main()
