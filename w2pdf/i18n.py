"""Interface strings for the web app, in English, French and Arabic.

The app itself can be shown in one language or in a duo pairing (Arabic with
French, Arabic with English); a duo label renders both texts side by side, the
Latin one first. The PDF output language is a separate setting and lives in
`app.py`, because it drives the document rather than the interface.
"""

from __future__ import annotations

DEFAULT_UI_MODE = "duo_fr"

# Which languages each interface mode shows, in display order.
UI_MODES: dict[str, tuple[str, ...]] = {
    "fr": ("fr",),
    "ar": ("ar",),
    "en": ("en",),
    "duo_fr": ("fr", "ar"),
    "duo_en": ("en", "ar"),
}

# Labels for the mode picker itself: each option is written in its own language.
UI_MODE_LABELS: dict[str, str] = {
    "fr": "Français",
    "ar": "العربية",
    "en": "English",
    "duo_fr": "Duo 1 — العربية / Français",
    "duo_en": "Duo 2 — العربية / English",
}

STRINGS: dict[str, dict[str, str]] = {
    # -- sidebar ---------------------------------------------------------
    "webapp": {
        "en": "Web app",
        "fr": "Application web",
        "ar": "تطبيق الويب",
    },
    "webapp_language": {
        "en": "Language of this page",
        "fr": "Langue de cette page",
        "ar": "لغة هذه الصفحة",
    },
    "webapp_language_help": {
        "en": "Choose one language, or a duo pairing that shows Arabic and the Latin "
        "language together on every page of the app.",
        "fr": "Choisissez une langue, ou un duo qui affiche l'arabe et la langue latine "
        "ensemble sur toutes les pages de l'application.",
        "ar": "اختر لغة واحدة، أو ازدواجاً يعرض العربية إلى جانب اللغة اللاتينية في كل صفحات التطبيق.",
    },
    "document": {"en": "Document", "fr": "Document", "ar": "المستند"},
    "title": {"en": "Title", "fr": "Titre", "ar": "العنوان"},
    "page_size": {"en": "Page size", "fr": "Format de page", "ar": "حجم الصفحة"},
    "orientation": {"en": "Orientation", "fr": "Orientation", "ar": "الاتجاه"},
    "portrait": {"en": "Portrait", "fr": "Portrait", "ar": "عمودي"},
    "landscape": {"en": "Landscape", "fr": "Paysage", "ar": "أفقي"},
    "margins": {"en": "Margins (mm)", "fr": "Marges (mm)", "ar": "الهوامش (مم)"},
    "images_per_page": {
        "en": "Images per page",
        "fr": "Images par page",
        "ar": "الصور في الصفحة",
    },
    "pdf_language": {
        "en": "PDF output language",
        "fr": "Langue du PDF",
        "ar": "لغة ملف PDF",
    },
    "pdf_language_help": {
        "en": "What the document prints: one language only, or the Arabic message with "
        "its French or English translation on every page.",
        "fr": "Ce que contient le document : une seule langue, ou le message arabe avec sa "
        "traduction française ou anglaise sur chaque page.",
        "ar": "ما يُطبع في الملف: لغة واحدة فقط، أو الرسالة العربية مع ترجمتها الفرنسية "
        "أو الإنجليزية في كل صفحة.",
    },
    "pdf_fr": {"en": "French", "fr": "Français", "ar": "الفرنسية"},
    "pdf_ar": {"en": "Arabic", "fr": "Arabe", "ar": "العربية"},
    "pdf_en": {"en": "English", "fr": "Anglais", "ar": "الإنجليزية"},
    "pdf_duo_fr": {
        "en": "Duo 1 — Arabic / French",
        "fr": "Duo 1 — Arabe / Français",
        "ar": "ثنائي 1 — العربية / الفرنسية",
    },
    "pdf_duo_en": {
        "en": "Duo 2 — Arabic / English",
        "fr": "Duo 2 — Arabe / Anglais",
        "ar": "ثنائي 2 — العربية / الإنجليزية",
    },
    "translate_note": {
        "en": "Arabic → {target}: MyMemory first, Google as fallback — no API key, "
        "needs internet.",
        "fr": "Arabe → {target} : MyMemory d'abord, Google en secours — sans clé d'API, "
        "connexion requise.",
        "ar": "العربية → {target}: MyMemory أولاً ثم Google — دون مفتاح، ويحتاج إنترنت.",
    },
    "extras": {"en": "Extras", "fr": "Options", "ar": "خيارات"},
    "show_metadata": {
        "en": "Show sender and date",
        "fr": "Afficher l'expéditeur et la date",
        "ar": "إظهار المرسل والتاريخ",
    },
    "page_numbers": {"en": "Page numbers", "fr": "Numéros de page", "ar": "أرقام الصفحات"},
    "save_copy": {
        "en": "Save a copy to the output folder",
        "fr": "Enregistrer une copie dans le dossier output",
        "ar": "حفظ نسخة في مجلد المخرجات",
    },
    "save_copy_help": {
        "en": "Keeps the PDF in output/ on the host. Turn it off to only download it.",
        "fr": "Garde le PDF dans output/ sur la machine. Désactivez pour seulement le "
        "télécharger.",
        "ar": "يحفظ الملف في مجلد output على جهازك. أوقفه للاكتفاء بالتنزيل.",
    },
    "font_warning": {
        "en": "No Arabic-capable font found. Arabic text will be refused; the image ships "
        "VIP Rawy in static/fonts, and Amiri/Noto are used as system fallbacks.",
        "fr": "Aucune police arabe trouvée. Le texte arabe sera refusé ; l'image fournit "
        "VIP Rawy dans static/fonts, et Amiri/Noto servent de secours système.",
        "ar": "لم يُعثر على خط يدعم العربية. سيُرفض النص العربي؛ الصورة تتضمن VIP Rawy في "
        "static/fonts وتُستخدم Amiri/Noto كبدائل.",
    },
    # -- hero and sections ------------------------------------------------
    "hero_title": {
        "en": "Turn an exported chat into one clean PDF",
        "fr": "Transformez un export de conversation en un PDF propre",
        "ar": "حوِّل محادثة مصدَّرة إلى ملف PDF منظم",
    },
    "hero_subtitle": {
        "en": "Upload the .zip you exported from WhatsApp, pick a date range, then tick "
        "the photos, videos and messages that belong in the document.",
        "fr": "Importez le .zip exporté depuis WhatsApp, choisissez une période, puis "
        "cochez les photos, vidéos et messages à inclure dans le document.",
        "ar": "ارفع ملف .zip المصدَّر من واتساب، اختر الفترة الزمنية، ثم حدد الصور "
        "والفيديوهات والرسائل التي تريدها في الملف.",
    },
    "section_export": {
        "en": "1 · WhatsApp export",
        "fr": "1 · Export WhatsApp",
        "ar": "1 · تصدير واتساب",
    },
    "uploader_label": {
        "en": "Chat export (.zip, with media)",
        "fr": "Export de la conversation (.zip, avec médias)",
        "ar": "تصدير المحادثة (.zip مع الوسائط)",
    },
    "uploader_help": {
        "en": "On your phone: open the chat → tap the contact or group name → Export "
        "chat → With all media. Upload the .zip unchanged; the chat log and its media "
        "are read inside it.",
        "fr": "Sur le téléphone : ouvrez la conversation → touchez le nom du contact ou "
        "du groupe → Exporter la discussion → Avec tous les médias. Importez le .zip "
        "tel quel ; le journal et ses médias sont lus à l'intérieur.",
        "ar": "على هاتفك: افتح المحادثة ← اسم الجهة ← تصدير المحادثة ← مع كل الوسائط. "
        "ارفع الملف كما هو، فسجل المحادثة والوسائط يُقرآن من داخله.",
    },
    "no_upload": {
        "en": "Export the chat from WhatsApp (**Export chat → With all media**), then "
        "drop the `.zip` above. The archive is read in memory — nothing is written to "
        "disk.",
        "fr": "Exportez la conversation depuis WhatsApp (**Exporter → Avec tous les "
        "médias**), puis déposez le `.zip` ci-dessus. L'archive est lue en mémoire — "
        "rien n'est écrit sur le disque.",
        "ar": "صدِّر المحادثة من واتساب (**تصدير المحادثة ← مع كل الوسائط**) ثم أسقط ملف "
        "`.zip` أعلاه. يُقرأ الأرشيف في الذاكرة دون كتابة على القرص.",
    },
    "no_messages_read": {
        "en": "No messages could be read from the chat log inside that archive.",
        "fr": "Aucun message n'a pu être lu dans le journal contenu dans cette archive.",
        "ar": "لم تُقرأ أي رسالة من سجل المحادثة داخل هذا الأرشيف.",
    },
    "date_range": {"en": "Date range", "fr": "Période", "ar": "الفترة الزمنية"},
    "date_range_help": {
        "en": "Only messages posted inside this range go into the PDF.",
        "fr": "Seuls les messages de cette période entrent dans le PDF.",
        "ar": "تُضمَّن في الملف رسائل هذه الفترة فقط.",
    },
    "caption_no_dates": {
        "en": "{count} messages · no dates found, so no date filter.",
        "fr": "{count} messages · aucune date trouvée, donc pas de filtre.",
        "ar": "{count} رسالة · لا تواريخ، لذا لا تصفية.",
    },
    "caption_range": {
        "en": "{selected} of {total} messages between {start} and {end}",
        "fr": "{selected} messages sur {total} entre le {start} et le {end}",
        "ar": "{selected} من {total} رسالة بين {start} و{end}",
    },
    "outside_range": {
        "en": "{count} outside the range",
        "fr": "{count} hors période",
        "ar": "{count} خارج الفترة",
    },
    "archive_counts": {
        "en": "{photos} photo(s) · {videos} video(s) · {audios} audio file(s) in the archive",
        "fr": "{photos} photo(s) · {videos} vidéo(s) · {audios} fichier(s) audio dans "
        "l'archive",
        "ar": "{photos} صورة · {videos} فيديو · {audios} ملف صوتي في الأرشيف",
    },
    "files_copied": {
        "en": "{count} file(s) copied to `{folder}` (the folder was emptied first).",
        "fr": "{count} fichier(s) copié(s) dans `{folder}` (dossier vidé au préalable).",
        "ar": "تم نسخ {count} ملف إلى `{folder}` (أُفرغ المجلد أولاً).",
    },
    "files_current": {
        "en": "Files already up to date in `{folder}`.",
        "fr": "Fichiers déjà à jour dans `{folder}`.",
        "ar": "الملفات محدثة بالفعل في `{folder}`.",
    },
    "files_failed": {
        "en": "Could not write the attachment files to the files folder.",
        "fr": "Impossible d'écrire les fichiers joints dans le dossier files.",
        "ar": "تعذّرت كتابة الملفات المرفقة في مجلد files.",
    },
    "no_rows": {
        "en": "No messages in the selected range.",
        "fr": "Aucun message dans la période choisie.",
        "ar": "لا رسائل في الفترة المحددة.",
    },
    # -- table -----------------------------------------------------------
    "col_include": {"en": "Include", "fr": "Inclure", "ar": "تضمين"},
    "col_seq": {"en": "Seq", "fr": "N°", "ar": "الترتيب"},
    "col_seq_help": {
        "en": "Document position, assigned in chat order so each photo keeps its message.",
        "fr": "Position dans le document, attribuée dans l'ordre de la conversation pour "
        "que chaque photo garde son message.",
        "ar": "موقع العنصر في الملف، بترتيب المحادثة كي تبقى كل صورة مع رسالتها.",
    },
    "col_type": {"en": "Type", "fr": "Type", "ar": "النوع"},
    "col_date": {"en": "Date", "fr": "Date", "ar": "التاريخ"},
    "col_sender": {"en": "Sender", "fr": "Expéditeur", "ar": "المرسل"},
    "col_content": {"en": "Content", "fr": "Contenu", "ar": "المحتوى"},
    "preview_title": {
        "en": "Preview media · {count} item(s)",
        "fr": "Aperçu des médias · {count} élément(s)",
        "ar": "معاينة الوسائط · {count} عنصر",
    },
    "preview_help": {
        "en": "Click an item to open the photo, play the video or listen to the voice "
        "note exactly as it was sent.",
        "fr": "Cliquez sur un élément pour ouvrir la photo, lire la vidéo ou écouter le "
        "message vocal tel qu'il a été envoyé.",
        "ar": "اضغط على عنصر لعرض الصورة أو تشغيل الفيديو أو سماع الرسالة الصوتية كما أُرسلت.",
    },
    "missing_video": {
        "en": "This video is not inside the archive.",
        "fr": "Cette vidéo n'est pas dans l'archive.",
        "ar": "هذا الفيديو غير موجود في الأرشيف.",
    },
    "missing_audio": {
        "en": "This voice note is not inside the archive.",
        "fr": "Ce message vocal n'est pas dans l'archive.",
        "ar": "هذه الرسالة الصوتية غير موجودة في الأرشيف.",
    },
    "selection_caption": {
        "en": "{items} item(s) selected · {photos} photo(s) · {videos} video(s) paired "
        "from the archive. Untick anything you do not want in the PDF.",
        "fr": "{items} élément(s) sélectionné(s) · {photos} photo(s) · {videos} vidéo(s) "
        "apparié(s) depuis l'archive. Décochez ce que vous ne voulez pas dans le PDF.",
        "ar": "{items} عنصر محدد · {photos} صورة · {videos} فيديو مرتبط من الأرشيف. "
        "أزل التحديد عمّا لا تريده في الملف.",
    },
    "section_build": {
        "en": "2 · Build the PDF",
        "fr": "2 · Générer le PDF",
        "ar": "2 · إنشاء ملف PDF",
    },
    "totals": {
        "en": "{photos} photo(s) · {videos} video(s) · {voice} voice message(s) · "
        "{texts} text block(s) · {arabic} to translate",
        "fr": "{photos} photo(s) · {videos} vidéo(s) · {voice} message(s) vocal(aux) · "
        "{texts} bloc(s) de texte · {arabic} à traduire",
        "ar": "{photos} صورة · {videos} فيديو · {voice} رسالة صوتية · {texts} نص · "
        "{arabic} للترجمة",
    },
    "order_title": {
        "en": "Document order · {count} item(s)",
        "fr": "Ordre du document · {count} élément(s)",
        "ar": "ترتيب الملف · {count} عنصر",
    },
    "kind_photo": {"en": "Photo", "fr": "Photo", "ar": "صورة"},
    "kind_video": {"en": "Video", "fr": "Vidéo", "ar": "فيديو"},
    "kind_text": {"en": "Text", "fr": "Texte", "ar": "نص"},
    "build": {"en": "Build PDF", "fr": "Générer le PDF", "ar": "إنشاء ملف PDF"},
    "build_nothing": {
        "en": "Upload an export and select at least one photo or text block.",
        "fr": "Importez un export et sélectionnez au moins une photo ou un bloc de texte.",
        "ar": "ارفع تصديراً وحدد صورة أو نصاً واحداً على الأقل.",
    },
    "translating": {
        "en": "Translating {count} Arabic block(s) to {target}…",
        "fr": "Traduction de {count} bloc(s) arabe(s) vers {target}…",
        "ar": "ترجمة {count} نص عربي إلى {target}…",
    },
    "translate_partial": {
        "en": "{failed} of {total} block(s) could not be translated; the original text "
        "is kept for those.",
        "fr": "{failed} bloc(s) sur {total} n'ont pas pu être traduits ; le texte "
        "d'origine est conservé.",
        "ar": "تعذّرت ترجمة {failed} من {total} نصاً؛ ويُحتفظ بالنص الأصلي لها.",
    },
    "frames": {
        "en": "Extracting a still frame from {count} video(s)…",
        "fr": "Extraction d'une image fixe de {count} vidéo(s)…",
        "ar": "استخراج صورة ثابتة من {count} فيديو…",
    },
    "laying_out": {
        "en": "Laying out the document…",
        "fr": "Mise en page du document…",
        "ar": "تنسيق الملف…",
    },
    "status_building": {
        "en": "Building the PDF…",
        "fr": "Génération du PDF…",
        "ar": "جارٍ إنشاء الملف…",
    },
    "status_error": {
        "en": "Could not build the PDF",
        "fr": "Impossible de générer le PDF",
        "ar": "تعذّر إنشاء الملف",
    },
    "build_error_unexpected": {
        "en": "Unexpected error while building the PDF: {error}",
        "fr": "Erreur inattendue pendant la génération du PDF : {error}",
        "ar": "خطأ غير متوقع أثناء إنشاء الملف: {error}",
    },
    "status_ready": {"en": "PDF ready", "fr": "PDF prêt", "ar": "الملف جاهز"},
    "pdf_ready": {"en": "Your PDF is ready", "fr": "Votre PDF est prêt", "ar": "ملف PDF جاهز"},
    "saved_copy": {
        "en": "Saved copy: `{path}` (the output folder mounted from your project).",
        "fr": "Copie enregistrée : `{path}` (dossier output monté depuis votre projet).",
        "ar": "نسخة محفوظة: `{path}` (مجلد المخرجات من مشروعك).",
    },
    "save_failed": {
        "en": "Could not write to the output folder, use the button below: {error}",
        "fr": "Impossible d'écrire dans le dossier output, utilisez le bouton ci-dessous : "
        "{error}",
        "ar": "تعذّرت الكتابة في مجلد المخرجات، استخدم الزر أدناه: {error}",
    },
    "saving_off": {
        "en": "Saving a copy is turned off, so use the button below.",
        "fr": "L'enregistrement d'une copie est désactivé, utilisez le bouton ci-dessous.",
        "ar": "حفظ النسخة متوقف، استخدم الزر أدناه.",
    },
    "download_pdf": {
        "en": "Download PDF locally",
        "fr": "Télécharger le PDF",
        "ar": "تنزيل ملف PDF",
    },
    "download_help": {
        "en": "Save the PDF to your computer through the browser.",
        "fr": "Enregistrez le PDF sur votre ordinateur via le navigateur.",
        "ar": "احفظ الملف على جهازك عبر المتصفح.",
    },
    "untranslated_title": {
        "en": "Untranslated blocks ({count})",
        "fr": "Blocs non traduits ({count})",
        "ar": "نصوص غير مترجمة ({count})",
    },
    "col_reason": {"en": "reason", "fr": "raison", "ar": "السبب"},
    "output_title": {
        "en": "Output folder · {count} recent file(s)",
        "fr": "Dossier output · {count} fichier(s) récent(s)",
        "ar": "مجلد المخرجات · {count} ملف حديث",
    },
    "output_help": {
        "en": "{path} — download any of them again:",
        "fr": "{path} — téléchargez à nouveau l'un d'eux :",
        "ar": "{path} — أعد تنزيل أي منها:",
    },
    "download": {"en": "Download", "fr": "Télécharger", "ar": "تنزيل"},
    "translations_title": {
        "en": "Translations ({count})",
        "fr": "Traductions ({count})",
        "ar": "الترجمات ({count})",
    },
    "col_source": {"en": "Arabic", "fr": "Arabe", "ar": "العربية"},
    "col_translation": {"en": "Translation", "fr": "Traduction", "ar": "الترجمة"},
}


def ui_text(key: str, mode: str = DEFAULT_UI_MODE, **values: object) -> str:
    """Render one interface string in every language the mode shows."""
    entry = STRINGS.get(key)
    if not entry:
        return key
    languages = UI_MODES.get(mode, UI_MODES[DEFAULT_UI_MODE])
    parts: list[str] = []
    for language in languages:
        text = entry.get(language) or entry.get("en") or ""
        if values:
            try:
                text = text.format(**values)
            except (KeyError, IndexError):
                pass
        if text and text not in parts:
            parts.append(text)
    return " / ".join(parts)
