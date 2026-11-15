# W2PDF — WhatsApp images & texts to PDF

[![version](https://img.shields.io/badge/version-1.2.0-128C7E?style=flat-square)](CHANGELOG.md)
[![changelog](https://img.shields.io/badge/changelog-view-6B7280?style=flat-square)](CHANGELOG.md)

<https://github.com/kouljihate/w2pdf>

A Streamlit app that turns selected WhatsApp photos and chat messages into one
PDF, with an Arabic → French translation module.

## What it does

- **Images**: upload the photos WhatsApp exported (`.jpg`, `.png`, `.webp`, `.bmp`),
  tick the ones you want, add an optional caption and choose 1 or 2 images per page.
  Files are ordered by name (WhatsApp names them chronologically) or by upload order.
- **Chat export**: upload the `.zip` WhatsApp produces with **With all media** (or
  **With selected media**): the archive is read in memory, its `_chat.txt` parsed and
  each photo paired with the message that sent it. A date range narrows the export;
  the remaining items are numbered sequentially. A `.txt` export (without media) and
  pasted text are supported too.
- **Sequence**: every object carries a `Seq` number that decides its place in the
  PDF. Photos default to 1, 3, 5 … and texts to 2, 4, 6 …, so each photo is followed
  by its own texts; change the numbers to regroup or reorder anything. The merged
  order is previewed before building.
- **Translation**: every selected block containing Arabic is translated to French.
  The PDF can contain the original only, the French only, or both side by side.
- **PDF options**: title, page size (A4/Letter/Legal), portrait or landscape,
  margins, sender/date labels and page numbers.
- Arabic is shaped with `arabic-reshaper` + `python-bidi` and drawn with an
  embedded Arabic font (Amiri), so right-to-left lines render correctly.

## Run with Docker (recommended)

```bash
docker compose up --build -d
```

Open <http://localhost:8501>. Logs: `docker compose logs -f`. Stop: `docker compose down`.

Without compose:

```bash
docker build -t w2pdf:local .
docker run --rm -p 8501:8501 w2pdf:local
```

The image installs `fonts-hosny-amiri` and `fonts-noto-core` so Arabic text
renders inside the PDF.

## Run without Docker

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Outside Docker the app looks for an Arabic font on the system (Amiri or Noto
Naskh on Linux, Tahoma on Windows, Geeza Pro on macOS). Without one it refuses
Arabic text rather than printing empty boxes.

## Translation notes

- Uses `deep-translator`'s keyless free backends: MyMemory first, Google as a
  fallback. No API key, but the container needs outbound internet access.
  Results are cached for 24 hours per text block.
- Long messages are split into chunks (400 chars for MyMemory, 4000 for Google).
- Only blocks that contain Arabic are sent to the translator; other text is
  passed through unchanged.
- Try the bundled sample: `sample_data/whatsapp_sample.txt`.

## Layout

```
app.py                  Streamlit UI
w2pdf/pdf_builder.py    ReportLab layout: images, wrapped RTL text, footer
w2pdf/whatsapp.py       WhatsApp chat export parser (media references, sequential items)
w2pdf/archive.py        Reads the .zip export: chat log plus photos, no disk writes
w2pdf/translate.py      Arabic → French translation
w2pdf/fonts.py          Arabic font discovery
Dockerfile              python:3.12-slim image with Arabic fonts
docker-compose.yml      one-command startup on port 8501
```
