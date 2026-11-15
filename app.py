"""W2PDF — Streamlit front end.

Select WhatsApp images and chat messages, optionally translate Arabic text to
French, and download a single PDF.
"""

from __future__ import annotations

import re
from datetime import datetime

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
from w2pdf.whatsapp import chat_items, decode_export, parse_chat, split_paragraphs

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
      <h1>Turn selected chats and photos into one clean PDF</h1>
      <p>Tick the images and messages you want, translate Arabic to French, then download the document.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

IMAGE_TYPES = ["jpg", "jpeg", "png", "webp", "bmp"]


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
        help="Every selected text block containing Arabic is translated and added to the PDF.",
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

    if not fonts.arabic_font_available():
        st.warning(
            "No Arabic-capable font found. Arabic text will be refused; the image ships "
            "VIP Rawy in static/fonts, and Amiri/Noto are used as system fallbacks."
        )

    st.divider()
    st.caption(f"W2PDF v{__version__}")

# ---------------------------------------------------------------------------
# 1 — images
# ---------------------------------------------------------------------------
st.subheader("1 · Images")
uploads = st.file_uploader(
    "Drop WhatsApp images here",
    type=IMAGE_TYPES,
    accept_multiple_files=True,
    help="JPG, PNG, WEBP or BMP. Photos exported by WhatsApp keep their capture date in the file name.",
)

image_blocks: list[ImageBlock] = []
if uploads:
    order = st.radio(
        "Order",
        ["File name (oldest first)", "Upload order"],
        horizontal=True,
        disabled=len(uploads) < 2,
    )
    files = (
        sorted(uploads, key=lambda f: f.name.lower())
        if order.startswith("File name")
        else list(uploads)
    )
    by_name = {f.name: f.getvalue() for f in files}

    signature = abs(hash(tuple((f.name, f.size) for f in files)))
    frame = pd.DataFrame(
        [
            {"include": True, "seq": 2 * index + 1, "image": f.name, "caption": ""}
            for index, f in enumerate(files)
        ]
    )
    edited = st.data_editor(
        frame,
        key=f"images-{signature}",
        hide_index=True,
        column_config={
            "include": st.column_config.CheckboxColumn("Include", width="small", default=True),
            "seq": st.column_config.NumberColumn(
                "Seq",
                width="small",
                step=1,
                help="Document position. Photos default to 1, 3, 5 … so their texts fit between them.",
            ),
            "image": st.column_config.TextColumn("Image", disabled=True, width="large"),
            "caption": st.column_config.TextColumn("Caption (optional)", width="medium"),
        },
    )
    image_blocks = [
        ImageBlock(
            name=row.image,
            data=by_name[row.image],
            caption=str(row.caption or "").strip(),
            sequence=sequence_of(row.seq, 2 * index + 1),
        )
        for index, row in enumerate(edited.itertuples())
        if row.include
    ]
    st.caption(
        "Seq sets the document order. Number a photo 1 and the texts that belong to it 2 "
        "to keep them together; repeat for the next photo."
    )

    with st.expander(f"Preview ({len(files)} image{'s' if len(files) != 1 else ''})"):
        preview = files[:12]
        for start in range(0, len(preview), 6):
            columns = st.columns(6)
            for column, upload in zip(columns, preview[start : start + 6]):
                with column:
                    st.image(upload.getvalue(), caption=upload.name, width="stretch")
        if len(files) > 12:
            st.caption(f"Showing the first 12 of {len(files)} images.")

# ---------------------------------------------------------------------------
# 2 — texts
# ---------------------------------------------------------------------------
st.subheader("2 · WhatsApp texts")
source = st.radio(
    "Where does the text come from?",
    ["WhatsApp export (.zip)", "WhatsApp export (.txt)", "Paste text"],
    horizontal=True,
)

export_blocks: list[ImageBlock | TextBlock] = []
text_rows: list[dict] = []

if source == "Paste text":
    pasted = st.text_area(
        "Arabic or French text",
        height=220,
        placeholder="الصق النص العربي هنا…  (or paste any text)",
    )
    per_paragraph = st.checkbox("One block per blank line", value=True)
    blocks = split_paragraphs(pasted) if per_paragraph else ([pasted.strip()] if pasted.strip() else [])
    text_rows = [
        {"text": block, "sender": "", "date": "", "seq": 2 * (index + 1)}
        for index, block in enumerate(blocks)
    ]
    if text_rows:
        st.caption(
            f"{len(text_rows)} text block{'s' if len(text_rows) != 1 else ''}, numbered "
            "2, 4, 6 … so they slot in after each photo."
        )
else:
    is_zip = source.endswith("(.zip)")
    upload = st.file_uploader(
        "WhatsApp export",
        type=["zip"] if is_zip else ["txt"],
        key="chat-export",
        help=(
            "WhatsApp → open the chat → ⋮ or contact name → Export chat → With all media "
            "(or With selected media). Upload the .zip unchanged; photos are read inside it."
            if is_zip
            else "WhatsApp → more options → Export chat → Without media."
        ),
    )

    messages = []
    images: dict[str, bytes] = {}
    if upload is not None:
        try:
            if is_zip:
                archive = load_chat_archive(upload.getvalue())
                messages = archive.messages
                images = archive.images
            else:
                messages = parse_chat(decode_export(upload.getvalue()))
        except ArchiveError as exc:
            st.error(str(exc))
        if not messages:
            st.warning("No messages could be read from that file.")

    if messages:
        dated = [message.timestamp for message in messages if message.timestamp]
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
            selected_messages = messages
            st.caption(f"{len(messages)} messages · no dates found, so no date filter.")
        else:
            selected_messages = [
                message
                for message in messages
                if message.timestamp is None
                or start_day <= message.timestamp.date() <= end_day
            ]
            outside = len(messages) - len(selected_messages)
            st.caption(
                f"{len(selected_messages)} of {len(messages)} messages between "
                f"{start_day:%d/%m/%Y} and {end_day:%d/%m/%Y}"
                + (f" · {outside} outside the range" if outside else "")
                + (f" · {len(images)} images in the archive" if images else "")
            )

        rows = chat_items(selected_messages, images)
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
# 3 — build
# ---------------------------------------------------------------------------
st.subheader("3 · Build the PDF")

paste_blocks = [
    TextBlock(
        text=row["text"],
        sender=row["sender"],
        timestamp=row["date"],
        sequence=row["seq"],
    )
    for row in text_rows
]
if export_blocks:
    document_blocks: list[ImageBlock | TextBlock] = list(export_blocks)
    if image_blocks or text_rows:
        st.info(
            "The chat export supplies both photos and texts, so the separate images and "
            "pasted text are left out of this document."
        )
else:
    document_blocks = list(image_blocks) + paste_blocks

photo_total = sum(1 for block in document_blocks if isinstance(block, ImageBlock))
text_total = len(document_blocks) - photo_total
arabic_blocks = [
    block.text
    for block in document_blocks
    if isinstance(block, TextBlock) and contains_arabic(block.text)
]

st.caption(
    f"{photo_total} photo{'s' if photo_total != 1 else ''} · "
    f"{text_total} text block{'s' if text_total != 1 else ''} · "
    f"{len(arabic_blocks)} to translate"
)

if document_blocks:
    preview_blocks = order_blocks(document_blocks)
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
    if not document_blocks:
        st.warning("Select at least one photo or one text block.")
    else:
        translations: dict[str, str] = {}
        unique_arabic = sorted({text for text in arabic_blocks})
        with st.status("Building the PDF…", expanded=True) as status:
            if translation_mode != "none" and unique_arabic:
                st.write(f"Translating {len(unique_arabic)} Arabic block(s) to French…")
                progress = st.progress(0.0)
                try:
                    for index, text in enumerate(unique_arabic, start=1):
                        translations[text] = translate_one(text)
                        progress.progress(index / len(unique_arabic))
                except TranslationError as exc:
                    status.update(label="Translation failed", state="error")
                    st.error(str(exc))
                    st.stop()
                progress.empty()

            st.write("Laying out the document…")
            for block in document_blocks:
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
                pdf_bytes = build_pdf(document_blocks, options)
            except PdfExportError as exc:
                status.update(label="Could not build the PDF", state="error")
                st.error(str(exc))
                st.stop()

            st.session_state["pdf"] = pdf_bytes
            st.session_state["pdf_name"] = safe_filename(title)
            st.session_state["translations"] = translations
            status.update(label="PDF ready", state="complete", expanded=False)

pdf = st.session_state.get("pdf")
if pdf:
    size_kb = len(pdf) / 1024
    st.success(f"{st.session_state['pdf_name']} · {size_kb:.0f} KB")
    st.download_button(
        "Download PDF",
        data=pdf,
        file_name=st.session_state["pdf_name"],
        mime="application/pdf",
        type="primary",
        width="stretch",
    )
    last_translations = st.session_state.get("translations") or {}
    if last_translations:
        with st.expander(f"Translations ({len(last_translations)})"):
            st.dataframe(
                pd.DataFrame(
                    [{"Arabic": source_text, "French": french} for source_text, french in last_translations.items()]
                ),
                hide_index=True,
            )
