from celery import shared_task

from rag_tutor.chunking import chunk_text
from rag_tutor.embeddings import embed_texts

_MIN_TEXT_LENGTH = 50


@shared_task
def index_content(source_type, source_id):
    from rag_tutor.models import ContentChunk

    text, title, subject = _load_source(source_type, source_id)
    if not text or len(text.strip()) < _MIN_TEXT_LENGTH:
        return {"status": "skipped", "reason": "empty_or_short"}

    chunks = chunk_text(text)
    if not chunks:
        return {"status": "skipped", "reason": "no_chunks"}

    embeddings = embed_texts(chunks)

    ContentChunk.objects.filter(
        source_type=source_type, source_id=source_id,
    ).delete()

    chunk_objects = [
        ContentChunk(
            subject=subject,
            source_type=source_type,
            source_id=source_id,
            source_title=title,
            chunk_index=i,
            text=chunk,
            embedding=embedding,
        )
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    ContentChunk.objects.bulk_create(chunk_objects)

    return {"status": "success", "chunks": len(chunk_objects)}


def _load_source(source_type, source_id):
    if source_type == "module":
        from module.models.module import Module
        obj = Module.objects.select_related("subject").get(pk=source_id)
        return obj.description or "", obj.file_name, obj.subject
    elif source_type == "activity":
        from activity.models.activity_model import Activity
        obj = Activity.objects.select_related("subject").get(pk=source_id)
        return obj.activity_instruction or "", obj.activity_name, obj.subject
    elif source_type == "chapter":
        from central_content.models import ParsedChapter
        obj = ParsedChapter.objects.select_related("textbook__central_subject").get(pk=source_id)
        parsed = obj.parsed_data or {}
        text = parsed.get("text", "") if isinstance(parsed, dict) else str(parsed)
        return text, obj.title, None
    raise ValueError(f"Unknown source_type: {source_type}")
