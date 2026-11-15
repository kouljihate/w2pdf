"""W2PDF — Streamlit front end.

Upload a WhatsApp chat export (.zip, including media), narrow it with a date
range, tick the messages and photos that belong in the PDF, and download it.
"""

from __future__ import annotations

import os
import re
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from w2pdf import __version__, fonts
from w2pdf.archive import ArchiveError, load_chat_archive
from w2pdf.pdf_builder import (
    TRANSLATION_MODE_LABELS,
    ImageBlock,
    PdfExportError,
    PdfOptions,
    TextBlock,
    build_pdf,
    order_blocks,
)
from w2pdf.translate import TranslationError, contains_arabic, translate_arabic_to_french
from w2pdf.whatsapp import chat_items

st.set_page_config(
    page_title="W2PDF · WhatsApp to PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

STYLE_FILES = ("static/theme/bootstrap-w2pdf.css", "static/css/app.css")


@st.cache_data(show_spinner=False)
def load_styles(*paths: str) -> str:
    """Inline the theme and app stylesheets so they always apply."""
    sheets = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                sheets.append(handle.read())
        except OSError:
            continue
    return "\n".join(sheets)


st.markdown(f"<style>{load_styles(*STYLE_FILES)}</style>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="w2p-hero">
      <div class="kicker">WhatsApp → PDF<span class="w2p-badge">v{__version__}</span></div>
      <h1>Turn an exported chat into one clean PDF</h1>
      <p>Upload the .zip you exported from WhatsApp, pick a date range, then tick the photos and messages
      that belong in the document.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def translate_one(text: str) -> str:
    """Translate a single Arabic block, cached across rebuilds."""
    return translate_arabic_to_french(text)


def sequence_of(value, fallback: int) -> float:
    """Read a sequence cell, falling back when it is empty or not a number."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return float(fallback) if number != number else number  # NaN guard


def safe_filename(title: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", (title or "").strip()).strip("-")
    return f"w2pdf-{stem or 'whatsapp-export'}-{datetime.now():%Y%m%d-%H%M}.pdf"


OUTPUT_DIR = Path(os.environ.get("W2PDF_OUTPUT_DIR", "output"))


def save_pdf_to_output(payload: bytes, filename: str) -> tuple[Path | None, str]:
    """Write the generated PDF into the output folder; report why when it fails."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        target = OUTPUT_DIR / filename
        target.write_bytes(payload)
        return target, ""
    except OSError as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Sidebar — document and translation settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Document")
    title = st.text_input("Title", value="WhatsApp export")
    page_size = st.selectbox("Page size", ["A4", "Letter", "Legal"], index=0)
    orientation = st.radio("Orientation", ["Portrait", "Landscape"], horizontal=True)
    margin_mm = st.slider("Margins (mm)", 8, 30, 15, 1)
    images_per_page = st.radio("Images per page", [1, 2], horizontal=True)

    st.divider()
    st.header("Translation")
    translate_on = st.toggle(
        "Arabic → French",
        value=True,
        help="Every selected message containing Arabic is translated and added to the PDF.",
    )
    mode_label = st.selectbox(
        "Text in the PDF",
        list(TRANSLATION_MODE_LABELS.values()),
        index=1,
        disabled=not translate_on,
    )
    translation_mode = "none"
    if translate_on:
        translation_mode = next(
            key for key, label in TRANSLATION_MODE_LABELS.items() if label == mode_label
        )
    st.caption("Free translation via MyMemory, Google as fallback — no API key, needs internet.")

    st.divider()
    st.header("Extras")
    show_metadata = st.checkbox("Show sender and date", value=True)
    page_numbers = st.checkbox("Page numbers", value=True)
    save_copies = st.checkbox(
        "Save a copy to the output folder",
        value=True,
        help="Keeps the PDF in output/ on the host. Turn it off to only download it.",
    )

    if not fonts.arabic_font_available():
        st.warning(
            "No Arabic-capable font found. Arabic text will be refused; the image ships "
            "VIP Rawy in static/fonts, and Amiri/Noto are used as system fallbacks."
        )

    st.divider()
    st.caption(f"W2PDF v{__version__}")

# ---------------------------------------------------------------------------
# 1 — the WhatsApp export
# ---------------------------------------------------------------------------
st.subheader("1 · WhatsApp export")

upload = st.file_uploader(
    "Chat export (.zip, with media)",
    type=["zip"],
    key="chat-export",
    help=(
        "On your phone: open the chat → tap the contact or group name → Export chat → "
        "With all media (or With selected media). Upload the .zip unchanged; the chat log "
        "and its photos are read inside it."
    ),
)

export_blocks: list[ImageBlock | TextBlock] = []

if upload is None:
    st.info(
        "Export the chat from WhatsApp (**Export chat → With all media**), then drop the "
        "`.zip` above. The archive is read in memory — nothing is written to disk."
    )
else:
    archive = None
    try:
        archive = load_chat_archive(upload.getvalue())
    except ArchiveError as exc:
        st.error(str(exc))

    if archive is not None and not archive.messages:
        st.warning("No messages could be read from the chat log inside that archive.")

    if archive is not None and archive.messages:
        dated = [message.timestamp for message in archive.messages if message.timestamp]
        if dated:
            first_day, last_day = min(dated).date(), max(dated).date()
            window = st.date_input(
                "Date range",
                value=(first_day, last_day),
                min_value=first_day,
                max_value=last_day,
                help="Only messages posted inside this range go into the PDF.",
            )
            if isinstance(window, (tuple, list)):
                start_day = window[0] if window else first_day
                end_day = window[-1] if len(window) > 1 else start_day
            else:
                start_day = end_day = window
            if start_day > end_day:
                start_day, end_day = end_day, start_day
        else:
            start_day = end_day = None

        if start_day is None or end_day is None:
            selected_messages = archive.messages
            st.caption(f"{len(archive.messages)} messages · no dates found, so no date filter.")
        else:
            selected_messages = [
                message
                for message in archive.messages
                if message.timestamp is None or start_day <= message.timestamp.date() <= end_day
            ]
            outside = len(archive.messages) - len(selected_messages)
            st.caption(
                f"{len(selected_messages)} of {len(archive.messages)} messages between "
                f"{start_day:%d/%m/%Y} and {end_day:%d/%m/%Y}"
                + (f" · {outside} outside the range" if outside else "")
                + f" · {len(archive.images)} photo(s) in the archive"
            )

        rows = chat_items(selected_messages, archive.images)
        if not rows:
            st.warning("No messages in the selected range.")
        else:
            signature = abs(hash((upload.name, upload.size, str(start_day), str(end_day))))
            frame = pd.DataFrame(
                [
                    {
                        "include": row["include"],
                        "seq": row["seq"],
                        "type": row["type"],
                        "date": row["date"],
                        "sender": row["sender"],
                        "content": row["content"],
                    }
                    for row in rows
                ]
            )
            edited = st.data_editor(
                frame,
                key=f"chat-{signature}",
                hide_index=True,
                height=min(520, 90 + 35 * len(rows)),
                column_config={
                    "include": st.column_config.CheckboxColumn(
                        "Include", width="small", default=True
                    ),
                    "seq": st.column_config.NumberColumn(
                        "Seq",
                        width="small",
                        step=1,
                        help="Document position, assigned in chat order so each photo keeps its message.",
                    ),
                    "type": st.column_config.TextColumn("Type", disabled=True, width="small"),
                    "date": st.column_config.TextColumn("Date", disabled=True, width="small"),
                    "sender": st.column_config.TextColumn("Sender", disabled=True, width="small"),
                    "content": st.column_config.TextColumn("Content", disabled=True, width="large"),
                },
            )
            for index, row in enumerate(edited.itertuples()):
                if not row.include:
                    continue
                source_row = rows[index]
                sequence = sequence_of(row.seq, source_row["seq"])
                if source_row["media"]:
                    export_blocks.append(
                        ImageBlock(
                            name=source_row["media"],
                            data=source_row["data"],
                            caption=source_row["caption"],
                            sequence=sequence,
                        )
                    )
                else:
                    export_blocks.append(
                        TextBlock(
                            text=source_row["text"],
                            sender=source_row["sender"],
                            timestamp=source_row["date"],
                            sequence=sequence,
                        )
                    )

            photos = sum(1 for block in export_blocks if isinstance(block, ImageBlock))
            st.caption(
                f"{len(export_blocks)} item(s) selected · {photos} photo(s) paired from the "
                "archive. Untick anything you do not want in the PDF."
            )

# ---------------------------------------------------------------------------
# 2 — build
# ---------------------------------------------------------------------------
st.subheader("2 · Build the PDF")

photo_total = sum(1 for block in export_blocks if isinstance(block, ImageBlock))
text_total = len(export_blocks) - photo_total
arabic_blocks = [
    block.text
    for block in export_blocks
    if isinstance(block, TextBlock) and contains_arabic(block.text)
]

st.caption(
    f"{photo_total} photo{'s' if photo_total != 1 else ''} · "
    f"{text_total} text block{'s' if text_total != 1 else ''} · "
    f"{len(arabic_blocks)} to translate"
)

if export_blocks:
    preview_blocks = order_blocks(export_blocks)
    with st.expander(f"Document order · {len(preview_blocks)} item(s)", expanded=False):
        preview_rows = []
        for block in preview_blocks:
            if isinstance(block, ImageBlock):
                content = f"Photo · {block.name}"
                if block.caption:
                    content += f" — {block.caption}"
            else:
                content = "Text · " + " ".join(block.text.split())[:90]
            preview_rows.append(
                {
                    "order": f"{block.sequence:g}",
                    "type": "Photo" if isinstance(block, ImageBlock) else "Text",
                    "content": content,
                }
            )
        st.dataframe(pd.DataFrame(preview_rows), hide_index=True)

build_clicked = st.button("Build PDF", type="primary", width="stretch")

if build_clicked:
    if not export_blocks:
        st.warning("Upload an export and select at least one photo or text block.")
        print("[w2pdf] build clicked with nothing selected", flush=True)
    else:
        translations: dict[str, str] = {}
        translation_errors: list[tuple[str, str]] = []
        unique_arabic = sorted({text for text in arabic_blocks})
        with st.status("Building the PDF…", expanded=True) as status:
            if translation_mode != "none" and unique_arabic:
                st.write(f"Translating {len(unique_arabic)} Arabic block(s) to French…")
                progress = st.progress(0.0)
                for index, text in enumerate(unique_arabic, start=1):
                    try:
                        translations[text] = translate_one(text)
                    except TranslationError as exc:
                        # Keep the original wording instead of losing the whole document.
                        translation_errors.append((text, str(exc)))
                    progress.progress(index / len(unique_arabic))
                progress.empty()
                if translation_errors:
                    st.warning(
                        f"{len(translation_errors)} of {len(unique_arabic)} block(s) could not be "
                        "translated; the original text is kept for those."
                    )

            st.write("Laying out the document…")
            for block in export_blocks:
                if isinstance(block, TextBlock):
                    block.translation = translations.get(block.text, "")

            options = PdfOptions(
                page_size=page_size,
                landscape=orientation == "Landscape",
                margin_mm=margin_mm,
                title=title,
                images_per_page=images_per_page,
                translation_mode=translation_mode,
                show_metadata=show_metadata,
                page_numbers=page_numbers,
            )
            try:
                pdf_bytes = build_pdf(export_blocks, options)
            except PdfExportError as exc:
                print(f"[w2pdf] build rejected: {exc}", flush=True)
                status.update(label="Could not build the PDF", state="error")
                st.error(str(exc))
                st.stop()
            except Exception as exc:  # unexpected: keep the reason in the server log
                traceback.print_exc()
                print(f"[w2pdf] build failed: {exc!r}", flush=True)
                status.update(label="Could not build the PDF", state="error")
                st.error(f"Unexpected error while building the PDF: {exc}")
                st.stop()

            filename = safe_filename(title)
            if save_copies:
                saved_path, save_error = save_pdf_to_output(pdf_bytes, filename)
            else:
                saved_path, save_error = None, ""
            st.session_state["pdf"] = pdf_bytes
            st.session_state["pdf_name"] = filename
            st.session_state["pdf_path"] = str(saved_path) if saved_path else ""
            st.session_state["pdf_save_error"] = save_error
            st.session_state["translations"] = translations
            st.session_state["translation_errors"] = translation_errors
            print(
                f"[w2pdf] built {filename}: {len(pdf_bytes)} bytes, "
                f"{len(export_blocks)} items, {len(translation_errors)} untranslated, "
                f"saved={saved_path or 'no'}",
                flush=True,
            )
            status.update(label="PDF ready", state="complete", expanded=False)
            st.toast("PDF ready", icon="✅")

pdf = st.session_state.get("pdf")
if pdf:
    size_kb = len(pdf) / 1024
    saved_path = st.session_state.get("pdf_path")
    with st.container(border=True):
        st.markdown("### Your PDF is ready")
        st.caption(f"{st.session_state['pdf_name']} · {size_kb:.0f} KB")
        if saved_path:
            st.caption(f"Saved copy: `{saved_path}` (the output folder mounted from your project).")
        elif st.session_state.get("pdf_save_error"):
            st.warning(
                "Could not write to the output folder, use the button below: "
                + st.session_state["pdf_save_error"]
            )
        else:
            st.caption("Saving a copy is turned off, so use the button below.")
        st.download_button(
            "Download PDF locally",
            data=pdf,
            file_name=st.session_state["pdf_name"],
            mime="application/pdf",
            type="primary",
            width="stretch",
            help="Save the PDF to your computer through the browser.",
        )

    failed_translations = st.session_state.get("translation_errors") or []
    if failed_translations:
        with st.expander(f"Untranslated blocks ({len(failed_translations)})"):
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Arabic": text, "reason": reason}
                        for text, reason in failed_translations
                    ]
                ),
                hide_index=True,
            )
    saved_files = sorted(
        (path for path in OUTPUT_DIR.glob("*.pdf") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:8] if OUTPUT_DIR.is_dir() else []
    if saved_files:
        with st.expander(f"Output folder · {len(saved_files)} recent file(s)"):
            st.caption(f"{OUTPUT_DIR.resolve()} — download any of them again:")
            for path in saved_files:
                file_col, size_col, action_col = st.columns([0.62, 0.18, 0.2])
                file_col.markdown(f"**{path.name}**")
                size_col.caption(
                    f"{path.stat().st_size / 1024:.0f} KB · "
                    f"{datetime.fromtimestamp(path.stat().st_mtime):%d/%m/%Y %H:%M}"
                )
                with action_col:
                    st.download_button(
                        "Download",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/pdf",
                        key=f"download-{path.name}",
                        width="stretch",
                    )

    last_translations = st.session_state.get("translations") or {}
    if last_translations:
        with st.expander(f"Translations ({len(last_translations)})"):
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Arabic": source_text, "French": french}
                        for source_text, french in last_translations.items()
                    ]
                ),
                hide_index=True,
            )
