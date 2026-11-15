# W2PDF — WhatsApp images & texts to PDF

[![version](https://img.shields.io/badge/version-1.5.0-128C7E?style=flat-square)](CHANGELOG.md)
[![changelog](https://img.shields.io/badge/changelog-view-6B7280?style=flat-square)](CHANGELOG.md)

<https://github.com/kouljihate/w2pdf>

A Streamlit app that turns selected WhatsApp photos and chat messages into one
PDF, with an Arabic → French translation module.

## What it does

- **One upload**: drop the `.zip` WhatsApp produces with **With all media** (or
  **With selected media**). The archive is read in memory, its `_chat.txt` parsed and
  each photo paired with the message that sent it — no separate image uploads.
- **Date range**: pick the days you want; messages outside the range are dropped and
  the remaining items are numbered sequentially.
- **Sequence**: every item carries a `Seq` number that decides its place in the PDF,
  assigned in chat order so each photo is followed by the messages that came with it.
  Change a number to reorder; the resulting order is previewed before building.
- **Translation**: every selected block containing Arabic is translated to French.
  The PDF can contain the original only, the French only, or both side by side.
- **PDF options**: title, page size (A4/Letter/Legal), portrait or landscape,
  margins, sender/date labels and page numbers.
- **Output folder**: every generated PDF is written to `output/` (`/app/output` in the
  container, mounted to `./output` by Compose) as well as offered for download;
  override the location with `W2PDF_OUTPUT_DIR`.
- Arabic is shaped with `arabic-reshaper` + `python-bidi` and drawn with an
  embedded Arabic font (VIP Rawy, Amiri fallback), so right-to-left lines render correctly.

## Run with Docker (recommended)

```bash
docker compose up --build -d
```

Open <http://localhost:8501>. Logs: `docker compose logs -f`. Stop: `docker compose down`.

Without compose:

```bash
docker build -t w2pdf:local .
docker run --rm -p 8501:8501 -v "$PWD/output:/app/output" w2pdf:local
```

Without the volume the container still writes to `/app/output` inside itself, so mount
the folder to keep the PDFs on your machine.

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

## Theming and fonts

- `static/theme/bootstrap-w2pdf.css` is a **free Bootstrap 5 design layer**: Bootstrap's
  colour, radius, spacing, shadow and component tokens (buttons, inputs, alerts,
  expanders, tables, uploader) applied to Streamlit's markup. Bootstrap's reset is
  deliberately not loaded — it would fight Streamlit's own layout.
- `static/css/app.css` holds app-specific pieces (hero, version badge).
- Typography is duo-language: **Comfortaa** (Light/Regular/Bold) for Latin and French,
  **VIP Rawy** (Regular/Bold) for Arabic. The CSS font stack falls back per glyph, and
  the PDF registers both faces with ReportLab (Amiri/Noto remain system fallbacks).
- Fonts are loaded from `static/fonts` through Streamlit's static serving
  (`server.enableStaticServing`, URL prefix `/app/static/`), so nothing is fetched online.
- Comfortaa ships in this repo under the SIL Open Font License
  (`static/fonts/OFL-Comfortaa.txt`). **VIP Rawy has no published license, so its
  binaries are not redistributed here** — copy `VIP-Rawy-Regular.ttf` and
  `VIP-Rawy-Bold.ttf` into `static/fonts/` for local builds (Arabic then falls back to
  Amiri/Noto when they are absent).

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
output/                 generated PDFs (mounted to /app/output by Compose)
static/fonts/           Comfortaa (Latin) and VIP Rawy (Arabic)
static/theme/           Bootstrap 5 design layer
static/css/             app-specific styles
```
