# Changelog

All notable changes to W2PDF. Versions follow [Semantic Versioning](https://semver.org/).

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
