"""W2PDF — Streamlit front end.

Upload a WhatsApp chat export (.zip, including media), narrow it with a date
range, tick the messages and photos that belong in the PDF, and download it.

Two language settings stay independent:
  * the web app's own language (one language or an Arabic duo pairing), and
  * the PDF output language (French, Arabic, English or one of two duo pairings).
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
from w2pdf.i18n import DEFAULT_UI_MODE, UI_MODE_LABELS, ui_text
from w2pdf.media import extract_video_frame
from w2pdf.pdf_builder import (
    ImageBlock,
    PdfExportError,
    PdfOptions,
    TextBlock,
    build_pdf,
    order_blocks,
)
from w2pdf.translate import TranslationError, contains_arabic, translate_arabic
from w2pdf.whatsapp import chat_items

st.set_page_config(
    page_title="W2PDF · WhatsApp to PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The Bootswatch Cyborg sheet is served from static/theme as a plain file; the two
# smaller sheets below are inlined so they always land after it and win the cascade.
BOOTSWATCH_HREF = "/app/static/theme/bootswatch-cyborg.min.css"
STYLE_FILES = ("static/theme/bootstrap-w2pdf.css", "static/css/app.css")
DUO_FONT_STACK = '"Comfortaa", "VIP Rawy", "Segoe UI", system-ui, sans-serif'

# PDF output language → (translation mode, translation target).
PDF_OUTPUT_MODES: dict[str, tuple[str, str]] = {
    "pdf_fr": ("translated", "fr"),
    "pdf_ar": ("none", "fr"),
    "pdf_en": ("translated", "en"),
    "pdf_duo_fr": ("both", "fr"),
    "pdf_duo_en": ("both", "en"),
}


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


st.markdown(f'<link rel="stylesheet" href="{BOOTSWATCH_HREF}">', unsafe_allow_html=True)
st.markdown(f"<style>{load_styles(*STYLE_FILES)}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def translate_one(text: str, target: str) -> str:
    """Translate a single Arabic block, cached per language across rebuilds."""
    return translate_arabic(text, target)


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
# Sidebar — interface language, document, PDF language, extras
# ---------------------------------------------------------------------------
# The picker is labelled in each language, so it is readable before a choice exists.
ui_header = "Langue · اللغة · Language"

with st.sidebar:
    st.header(ui_header)
    ui_language = st.radio(
        ui_header,
        list(UI_MODE_LABELS),
        index=list(UI_MODE_LABELS).index(DEFAULT_UI_MODE),
        format_func=lambda mode: UI_MODE_LABELS[mode],
        label_visibility="collapsed",
        key="ui-language",
    )

    def t(key: str, **values: object) -> str:
        """Translate an interface string into the languages this page shows."""
        return ui_text(key, ui_language, **values)

    st.caption(t("webapp_language_help"))

    st.divider()
    st.header(t("document"))
    title = st.text_input(t("title"), value="WhatsApp export")
    page_size = st.selectbox(t("page_size"), ["A4", "Letter", "Legal"], index=0)
    orientation = st.radio(
        t("orientation"),
        ["Portrait", "Landscape"],
        format_func=lambda value: t("portrait" if value == "Portrait" else "landscape"),
        horizontal=True,
    )
    margin_mm = st.slider(t("margins"), 8, 30, 15, 1)

    st.divider()
    st.header(t("pdf_language"))
    pdf_language = st.radio(
        t("pdf_language"),
        list(PDF_OUTPUT_MODES),
        index=list(PDF_OUTPUT_MODES).index("pdf_duo_fr"),
        format_func=lambda key: t(key),
        label_visibility="collapsed",
        key="pdf-language",
        help=t("pdf_language_help"),
    )
    translation_mode, target_language = PDF_OUTPUT_MODES[pdf_language]
    if translation_mode != "none":
        st.caption(t("translate_note", target=t(f"pdf_{target_language}")))

    st.divider()
    st.header(t("extras"))
    # Off by default: generated documents carry the messages without sender/date lines.
    show_metadata = st.checkbox(t("show_metadata"), value=False)
    page_numbers = st.checkbox(t("page_numbers"), value=True)
    save_copies = st.checkbox(
        t("save_copy"),
        value=True,
        help=t("save_copy_help"),
    )

    if not fonts.arabic_font_available():
        st.warning(t("font_warning"))

    st.divider()
    st.markdown(
        f'<div class="w2p-sidebar-footer">'
        f'<span class="w2p-badge w2p-badge--version">v{__version__}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

# Every theme rule reads this variable: Comfortaa for Latin, VIP Rawy for Arabic.
st.markdown(
    f"<style>:root {{ --bs-body-font-family: {DUO_FONT_STACK}; }}</style>",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="w2p-hero">
      <div class="kicker">WhatsApp → PDF<span class="w2p-badge">v{__version__}</span></div>
      <h1>{t("hero_title")}</h1>
      <p>{t("hero_subtitle")}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 1 — the WhatsApp export
# ---------------------------------------------------------------------------
st.subheader(t("section_export"))

upload = st.file_uploader(
    t("uploader_label"),
    type=["zip"],
    key="chat-export",
    help=t("uploader_help"),
)

export_blocks: list[ImageBlock | TextBlock] = []
archive = None

if upload is None:
    st.info(t("no_upload"))
else:
    try:
        archive = load_chat_archive(upload.getvalue())
    except ArchiveError as exc:
        st.error(str(exc))

    if archive is not None and not archive.messages:
        st.warning(t("no_messages_read"))

    if archive is not None and archive.messages:
        dated = [message.timestamp for message in archive.messages if message.timestamp]
        if dated:
            first_day, last_day = min(dated).date(), max(dated).date()
            window = st.date_input(
                t("date_range"),
                value=(first_day, last_day),
                min_value=first_day,
                max_value=last_day,
                help=t("date_range_help"),
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
            st.caption(t("caption_no_dates", count=len(archive.messages)))
        else:
            selected_messages = [
                message
                for message in archive.messages
                if message.timestamp is None or start_day <= message.timestamp.date() <= end_day
            ]
            outside = len(archive.messages) - len(selected_messages)
            summary = t(
                "caption_range",
                selected=len(selected_messages),
                total=len(archive.messages),
                start=f"{start_day:%d/%m/%Y}",
                end=f"{end_day:%d/%m/%Y}",
            )
            if outside:
                summary += " · " + t("outside_range", count=outside)
            summary += " · " + t(
                "archive_counts",
                photos=len(archive.images),
                videos=len(archive.videos),
                audios=len(archive.audios),
            )
            st.caption(summary)

        if archive.stored_files > 0:
            st.caption(t("files_copied", count=archive.stored_files, folder=archive.files_dir))
        elif archive.stored_files == 0:
            st.caption(t("files_current", folder=archive.files_dir))
        else:
            st.warning(t("files_failed"))

        rows = chat_items(selected_messages, archive.images, archive.videos, archive.audios)
        if not rows:
            st.warning(t("no_rows"))
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
                        t("col_include"), width="small", default=True
                    ),
                    "seq": st.column_config.NumberColumn(
                        t("col_seq"),
                        width="small",
                        step=1,
                        help=t("col_seq_help"),
                    ),
                    "type": st.column_config.TextColumn(
                        t("col_type"), disabled=True, width="small"
                    ),
                    "date": st.column_config.TextColumn(
                        t("col_date"), disabled=True, width="medium"
                    ),
                    "sender": st.column_config.TextColumn(
                        t("col_sender"), disabled=True, width="small"
                    ),
                    "content": st.column_config.TextColumn(
                        t("col_content"), disabled=True, width="large"
                    ),
                },
            )
            for index, row in enumerate(edited.itertuples()):
                if not row.include:
                    continue
                source_row = rows[index]
                sequence = sequence_of(row.seq, source_row["seq"])
                if source_row["type"] == "Video":
                    export_blocks.append(
                        ImageBlock(
                            name=source_row["media"],
                            data=b"",
                            caption=source_row["caption"],
                            sequence=sequence,
                            kind="video",
                        )
                    )
                elif source_row["type"] == "Audio":
                    export_blocks.append(
                        TextBlock(
                            text=source_row["text"],
                            sender=source_row["sender"],
                            timestamp=source_row.get("date_full") or source_row["date"],
                            sequence=sequence,
                        )
                    )
                elif source_row["media"]:
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
                            timestamp=source_row.get("date_full") or source_row["date"],
                            sequence=sequence,
                        )
                    )

            media_rows = [row for row in rows if row["type"] in {"Photo", "Video", "Audio"}]
            if media_rows:
                with st.expander(
                    t("preview_title", count=len(media_rows)), expanded=False
                ):
                    st.caption(t("preview_help"))
                    media_columns = st.columns(3)
                    for index, row in enumerate(media_rows):
                        label = " ".join(row["content"].split())[:40] or row["media"]
                        with media_columns[index % 3]:
                            with st.popover(label, width="stretch"):
                                if row["type"] == "Photo":
                                    st.image(row["data"], caption=row["media"])
                                elif row["type"] == "Video":
                                    video_payload = archive.video_for(row["media"])
                                    if video_payload:
                                        st.video(video_payload)
                                    else:
                                        st.caption(t("missing_video"))
                                else:
                                    audio_payload = archive.audio_for(row["media"])
                                    if audio_payload:
                                        st.audio(audio_payload)
                                    else:
                                        st.caption(t("missing_audio"))

            photos = sum(
                1
                for block in export_blocks
                if isinstance(block, ImageBlock) and block.kind == "photo"
            )
            videos = sum(
                1
                for block in export_blocks
                if isinstance(block, ImageBlock) and block.kind == "video"
            )
            st.caption(
                t(
                    "selection_caption",
                    items=len(export_blocks),
                    photos=photos,
                    videos=videos,
                )
            )

# ---------------------------------------------------------------------------
# 2 — build
# ---------------------------------------------------------------------------
st.subheader(t("section_build"))

photo_total = sum(
    1 for block in export_blocks if isinstance(block, ImageBlock) and block.kind == "photo"
)
video_total = sum(
    1 for block in export_blocks if isinstance(block, ImageBlock) and block.kind == "video"
)
audio_total = sum(
    1
    for block in export_blocks
    if isinstance(block, TextBlock) and block.text.startswith("Voice message")
)
text_total = len(export_blocks) - photo_total - video_total - audio_total
arabic_blocks = [
    block.text
    for block in export_blocks
    if isinstance(block, TextBlock) and contains_arabic(block.text)
]

st.caption(
    t(
        "totals",
        photos=photo_total,
        videos=video_total,
        voice=audio_total,
        texts=text_total,
        arabic=len(arabic_blocks),
    )
)

if export_blocks:
    preview_blocks = order_blocks(export_blocks)
    with st.expander(t("order_title", count=len(preview_blocks)), expanded=False):
        preview_rows = []
        for block in preview_blocks:
            if isinstance(block, ImageBlock):
                label = t("kind_video") if block.kind == "video" else t("kind_photo")
                content = f"{label} · {block.name}"
                if block.caption:
                    content += f" — {block.caption}"
            else:
                label = t("kind_text")
                content = f"{label} · " + " ".join(block.text.split())[:90]
            preview_rows.append(
                {
                    "order": f"{block.sequence:g}",
                    "type": label,
                    "content": content,
                }
            )
        st.dataframe(pd.DataFrame(preview_rows), hide_index=True)

build_clicked = st.button(t("build"), type="primary", width="stretch")

if build_clicked:
    if not export_blocks:
        st.warning(t("build_nothing"))
        print("[w2pdf] build clicked with nothing selected", flush=True)
    else:
        translations: dict[str, str] = {}
        translation_errors: list[tuple[str, str]] = []
        unique_arabic = sorted({text for text in arabic_blocks})
        with st.status(t("status_building"), expanded=True) as status:
            if translation_mode != "none" and unique_arabic:
                st.write(
                    t(
                        "translating",
                        count=len(unique_arabic),
                        target=t(f"pdf_{target_language}"),
                    )
                )
                progress = st.progress(0.0)
                for index, text in enumerate(unique_arabic, start=1):
                    try:
                        translations[text] = translate_one(text, target_language)
                    except TranslationError as exc:
                        # Keep the original wording instead of losing the whole document.
                        translation_errors.append((text, str(exc)))
                    progress.progress(index / len(unique_arabic))
                progress.empty()
                if translation_errors:
                    st.warning(
                        t(
                            "translate_partial",
                            failed=len(translation_errors),
                            total=len(unique_arabic),
                        )
                    )

            pending_videos = [
                block
                for block in export_blocks
                if isinstance(block, ImageBlock) and block.kind == "video" and not block.data
            ]
            if pending_videos:
                st.write(t("frames", count=len(pending_videos)))
                frame_progress = st.progress(0.0)
                for index, block in enumerate(pending_videos, start=1):
                    payload = archive.video_for(block.name) if archive else None
                    frame = extract_video_frame(payload) if payload else None
                    if frame:
                        block.data = frame
                    else:
                        print(f"[w2pdf] no frame for {block.name}", flush=True)
                    frame_progress.progress(index / len(pending_videos))
                frame_progress.empty()

            st.write(t("laying_out"))
            for block in export_blocks:
                if isinstance(block, TextBlock):
                    block.translation = translations.get(block.text, "")

            options = PdfOptions(
                page_size=page_size,
                landscape=orientation == "Landscape",
                margin_mm=margin_mm,
                title=title,
                translation_mode=translation_mode,
                target_language=target_language,
                show_metadata=show_metadata,
                page_numbers=page_numbers,
            )
            try:
                pdf_bytes = build_pdf(export_blocks, options)
            except PdfExportError as exc:
                print(f"[w2pdf] build rejected: {exc}", flush=True)
                status.update(label=t("status_error"), state="error")
                st.error(str(exc))
                st.stop()
            except Exception as exc:  # unexpected: keep the reason in the server log
                traceback.print_exc()
                print(f"[w2pdf] build failed: {exc!r}", flush=True)
                status.update(label=t("status_error"), state="error")
                st.error(t("build_error_unexpected", error=exc))
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
            st.session_state["pdf_language"] = pdf_language
            print(
                f"[w2pdf] built {filename}: {len(pdf_bytes)} bytes, "
                f"{len(export_blocks)} items, {len(translation_errors)} untranslated, "
                f"language={pdf_language}, saved={saved_path or 'no'}",
                flush=True,
            )
            status.update(label=t("status_ready"), state="complete", expanded=False)
            st.toast(t("status_ready"), icon="✅")

pdf = st.session_state.get("pdf")
if pdf:
    size_kb = len(pdf) / 1024
    saved_path = st.session_state.get("pdf_path")
    with st.container(border=True):
        st.markdown(f"### {t('pdf_ready')}")
        st.caption(f"{st.session_state['pdf_name']} · {size_kb:.0f} KB")
        if saved_path:
            st.caption(t("saved_copy", path=saved_path))
        elif st.session_state.get("pdf_save_error"):
            st.warning(
                t("save_failed", error=st.session_state["pdf_save_error"])
            )
        else:
            st.caption(t("saving_off"))
        st.download_button(
            t("download_pdf"),
            data=pdf,
            file_name=st.session_state["pdf_name"],
            mime="application/pdf",
            type="primary",
            width="stretch",
            help=t("download_help"),
        )

    failed_translations = st.session_state.get("translation_errors") or []
    if failed_translations:
        with st.expander(t("untranslated_title", count=len(failed_translations))):
            st.dataframe(
                pd.DataFrame(
                    [
                        {t("col_source"): text, t("col_reason"): reason}
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
        with st.expander(t("output_title", count=len(saved_files))):
            st.caption(t("output_help", path=OUTPUT_DIR.resolve()))
            for path in saved_files:
                file_col, size_col, action_col = st.columns([0.62, 0.18, 0.2])
                file_col.markdown(f"**{path.name}**")
                size_col.caption(
                    f"{path.stat().st_size / 1024:.0f} KB · "
                    f"{datetime.fromtimestamp(path.stat().st_mtime):%d/%m/%Y %H:%M}"
                )
                with action_col:
                    st.download_button(
                        t("download"),
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/pdf",
                        key=f"download-{path.name}",
                        width="stretch",
                    )

    last_translations = st.session_state.get("translations") or {}
    if last_translations:
        with st.expander(t("translations_title", count=len(last_translations))):
            st.dataframe(
                pd.DataFrame(
                    [
                        {t("col_source"): source_text, t("col_translation"): translated}
                        for source_text, translated in last_translations.items()
                    ]
                ),
                hide_index=True,
            )
