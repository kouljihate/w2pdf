# Changelog

All notable changes to W2PDF. Versions follow [Semantic Versioning](https://semver.org/).

## 1.7.0 — 2026-11-16

- Process the export like WhatsApp does: translate text, embed photos, grab a video frame, skip Facebook links

## 1.6.2 — 2026-11-15

- Keep the PDF when a translation fails and show the result in a dedicated panel

## 1.6.1 — 2026-11-15

- Bump the version on every change with a single release helper

## 1.6.0 — 2026-11-15

- The finished PDF can always be **downloaded locally** ("Download PDF locally").
- Saving a copy to the output folder is now optional ("Save a copy to the output folder").
- Files already in the output folder can be downloaded again from the app.

## 1.5.0 — 2026-11-15

- Every generated PDF is also written to the **output folder** (`output/` on the host,
  `/app/output` in the container, override with `W2PDF_OUTPUT_DIR`), not just offered
  as a download.
- The app reports the saved path and lists the most recent files in that folder.
- Docker Compose mounts `./output` so documents appear directly on your machine.

## 1.4.0 — 2026-11-15

- The app is now ZIP-first: upload the WhatsApp export, pick a date range, then tick
  photos and messages in one table. The separate image uploader, the `.txt` source and
  pasted text were removed from the UI to make that flow the only path.
- Item selection shows the date range summary and the number of photos found.

## 1.3.0 — 2026-11-15

- Bootstrap-flavoured theme layer (`static/theme/bootstrap-w2pdf.css`) built on
  Bootstrap 5 tokens and applied to Streamlit components.
- Duo-language typography: **Comfortaa** for Latin/French and **VIP Rawy** for
  Arabic, in the UI and in the generated PDF (Amiri/Noto remain as fallbacks).
- Local fonts served through Streamlit static serving, so the theme works offline.
- App-specific styles moved to `static/css/app.css`.

## 1.2.0 — 2026-11-15

- Upload a WhatsApp chat export **.zip** (with media) directly: the archive is read
  in memory, its `_chat.txt` parsed and each photo paired with the message that
  sent it.
- Date-range filter for exports; items are re-numbered sequentially after filtering.
- Chat exports produce one sequential table (Include · Seq · Type · Date · Sender ·
  Content) so photos and texts are selected together.
- Attachments missing from the archive fall back to an `Attachment: <name>` line.

## 1.1.1 — 2026-11-15

- Version number shown as a badge in the app header and in the README.

## 1.1.0 — 2026-11-15

- Every image and text block now carries a `Seq` number; the PDF is laid out in
  that sequence, so each photo can be followed by its own texts.
- Photos numbered consecutively still share a gallery page when "2 images per page"
  is selected.
- Added a "Document order" preview before building the PDF.
- The app shows its version in the sidebar.

## 1.0.0 — 2026-11-15

- Streamlit app that turns selected WhatsApp images and chat messages into a PDF.
- Arabic → French translation (MyMemory first, Google fallback) with original,
  translated, or bilingual output.
- WhatsApp "Export chat" `.txt` parser with per-message selection, plus pasted text.
- ReportLab layout with shaped RTL Arabic, captions, page sizes, margins,
  sender/date labels and page numbers.
- Docker image with Amiri/Noto fonts, non-root user and a healthcheck.
