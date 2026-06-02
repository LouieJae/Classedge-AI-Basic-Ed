import io
import re
import tempfile

import fitz
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from cache import file_hash, get_cached, put_cache

app = FastAPI(title="MinerU PDF Parser")


@app.get("/health")
def health():
    return {"status": "ok"}


def _extract_toc(doc: fitz.Document) -> list[dict]:
    toc = doc.get_toc(simple=True)
    if not toc:
        return _fallback_chapters(doc)

    chapters = []
    for i, (level, title, page) in enumerate(toc):
        if level > 1:
            continue
        start_page = page
        end_page = toc[i + 1][2] - 1 if i + 1 < len(toc) else doc.page_count
        chapters.append({
            "number": len(chapters) + 1,
            "title": title.strip(),
            "start_page": start_page,
            "end_page": end_page,
        })
    return chapters


def _fallback_chapters(doc: fitz.Document) -> list[dict]:
    chapter_pattern = re.compile(
        r"^(chapter|unit|module|lesson)\s+\d+", re.IGNORECASE
    )
    chapters = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                text = "".join(span["text"] for span in line["spans"]).strip()
                max_size = max((span["size"] for span in line["spans"]), default=0)
                if max_size >= 16 and chapter_pattern.match(text):
                    if chapters:
                        chapters[-1]["end_page"] = page_num
                    chapters.append({
                        "number": len(chapters) + 1,
                        "title": text,
                        "start_page": page_num + 1,
                        "end_page": doc.page_count,
                    })
    if not chapters:
        chapters.append({
            "number": 1,
            "title": "Full Document",
            "start_page": 1,
            "end_page": doc.page_count,
        })
    return chapters


@app.post("/parse/toc")
async def parse_toc(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty_file")

    sha = file_hash(contents)
    cached = get_cached(sha, "toc")
    if cached:
        return JSONResponse(content=cached)

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_pdf")

    chapters = _extract_toc(doc)
    title = doc.metadata.get("title", "") or file.filename or "Untitled"

    result = {
        "title": title.replace(".pdf", ""),
        "total_pages": doc.page_count,
        "chapters": chapters,
    }
    doc.close()

    put_cache(sha, "toc", result)
    return JSONResponse(content=result)


def _parse_page_text(page: fitz.Page) -> list[dict]:
    blocks = page.get_text("dict")["blocks"]
    sections = []
    current_heading = ""
    current_text_parts = []

    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            max_size = max((span["size"] for span in line["spans"]), default=0)
            is_bold = any(
                "bold" in (span.get("font", "").lower()) for span in line["spans"]
            )
            if max_size >= 13 and is_bold and len(text) < 200:
                if current_heading or current_text_parts:
                    sections.append({
                        "heading": current_heading,
                        "text": " ".join(current_text_parts),
                    })
                current_heading = text
                current_text_parts = []
            else:
                current_text_parts.append(text)

    if current_heading or current_text_parts:
        sections.append({
            "heading": current_heading,
            "text": " ".join(current_text_parts),
        })
    return sections


@app.post("/parse/chapter")
async def parse_chapter(
    file: UploadFile = File(...),
    start_page: int = Form(...),
    end_page: int = Form(...),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty_file")

    sha = file_hash(contents)
    cache_suffix = f"ch{start_page}_{end_page}"
    cached = get_cached(sha, cache_suffix)
    if cached:
        return JSONResponse(content=cached)

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_pdf")

    if start_page < 1 or end_page > doc.page_count or start_page > end_page:
        doc.close()
        raise HTTPException(status_code=400, detail="invalid_page_range")

    all_sections = []
    images = []
    for page_num in range(start_page - 1, end_page):
        page = doc.load_page(page_num)
        all_sections.extend(_parse_page_text(page))
        for img_index, img in enumerate(page.get_images(full=True)):
            images.append(f"page{page_num + 1}_img{img_index + 1}")

    result = {
        "start_page": start_page,
        "end_page": end_page,
        "sections": all_sections,
        "images": images,
    }
    doc.close()

    put_cache(sha, cache_suffix, result)
    return JSONResponse(content=result)
