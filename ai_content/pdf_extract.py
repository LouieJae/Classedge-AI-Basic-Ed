import fitz

_MAX_TEXT_LENGTH = 8000


def extract_text_from_pdf(file_field):
    if file_field is None:
        return ""
    try:
        file_bytes = file_field.read()
        file_field.seek(0)
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text())
        doc.close()
        full_text = "\n".join(pages_text).strip()
        return full_text[:_MAX_TEXT_LENGTH]
    except Exception:
        return ""
