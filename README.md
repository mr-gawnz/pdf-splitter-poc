# PDF Half Splitter POC

A small local Streamlit app that splits a landscape PDF spread vertically while avoiding rasterization.

## Why this approach

The splitter duplicates each eligible PDF page **inside the same document** and changes its page boxes so that one copy exposes the left half and the other exposes the right half.

It does **not** render the page to an image and rebuild it. This gives us a much better chance of preserving:

- vector content
- selectable text and embedded fonts
- URL/link annotations
- Optional Content Groups (PDF layers)
- transparency and other page resources

This is intentionally a POC. The first thing to validate with real iPaper/customer PDFs is whether links, OCG layers and unusual page rotations behave correctly in Adobe Acrobat and the iPaper import pipeline.

## Run on Windows

1. Install Python 3.11 or newer.
2. Open PowerShell in this folder.
3. Create a virtual environment:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
```

5. Start the app:

```powershell
streamlit run app.py
```

Your browser should open automatically.

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
