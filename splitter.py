from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Literal

import pikepdf

SplitOrder = Literal["left-right", "right-left"]


@dataclass
class SplitStats:
    input_pages: int = 0
    split_pages: int = 0
    untouched_pages: int = 0


def _set_page_box(page: pikepdf.Page, box: tuple[float, float, float, float]) -> None:
    arr = pikepdf.Array(box)
    # Keep the visible/print boxes aligned. The content stream itself is untouched.
    page.mediabox = arr
    page.cropbox = arr
    page.trimbox = arr
    page.bleedbox = arr
    page.artbox = arr


def _copy_page_in_place(pdf: pikepdf.Pdf, page_index: int) -> pikepdf.Page:
    """Insert a shallow copy of an existing page immediately after it.

    This preserves the original page resources/content streams and document-level
    structures such as Optional Content Groups (layers).
    """
    source = pdf.pages[page_index]
    pdf.pages.insert(page_index + 1, source)
    return pdf.pages[page_index + 1]


def split_pdf_bytes(
    data: bytes,
    *,
    only_landscape: bool = True,
    order: SplitOrder = "left-right",
) -> tuple[bytes, SplitStats]:
    """Split pages vertically by changing page boxes, without rasterizing content.

    Each eligible page is duplicated inside the same PDF. Both copies retain the
    original content/resources/annotations; their page boxes expose only one half.
    Because the document itself is retained, document-level optional-content/layer
    definitions remain present.
    """
    src = BytesIO(data)
    out = BytesIO()
    stats = SplitStats()

    with pikepdf.Pdf.open(src) as pdf:
        stats.input_pages = len(pdf.pages)
        i = 0
        while i < len(pdf.pages):
            page = pdf.pages[i]
            mb = [float(x) for x in page.mediabox]
            x0, y0, x1, y1 = mb
            width = x1 - x0
            height = y1 - y0

            eligible = width > height if only_landscape else True
            if not eligible:
                stats.untouched_pages += 1
                i += 1
                continue

            midpoint = x0 + width / 2.0
            left_box = (x0, y0, midpoint, y1)
            right_box = (midpoint, y0, x1, y1)

            duplicate = _copy_page_in_place(pdf, i)
            first = pdf.pages[i]
            second = duplicate

            if order == "left-right":
                _set_page_box(first, left_box)
                _set_page_box(second, right_box)
            else:
                _set_page_box(first, right_box)
                _set_page_box(second, left_box)

            stats.split_pages += 1
            i += 2

        pdf.save(out)

    return out.getvalue(), stats
