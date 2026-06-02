import os

import anthropic
from django.conf import settings
from pgvector.django import CosineDistance

from rag_tutor.embeddings import embed_texts
from rag_tutor.models import ChatMessage, ContentChunk

_SYSTEM_PROMPT = """You are a helpful tutor for a school course. Answer the student's \
question using ONLY the provided course material excerpts. Be clear, educational, and \
appropriate for a school setting.

If the provided excerpts contain relevant information, answer the question and cite which \
source you used (e.g., "According to Module 3...").

If the provided excerpts do NOT contain information to answer the question, respond with: \
"Your course materials don't cover this topic yet. You might want to ask your teacher \
about it, or search for the topic on Khan Academy (khanacademy.org)."

Do not make up information. Do not answer questions unrelated to academics."""


def ask_question(subject_id, question, student):
    question_embedding = embed_texts([question])[0]

    top_k = settings.RAG_TUTOR_TOP_K
    chunks = (
        ContentChunk.objects
        .filter(subject_id=subject_id)
        .annotate(distance=CosineDistance("embedding", question_embedding))
        .order_by("distance")[:top_k]
    )
    chunks = list(chunks)

    threshold = settings.RAG_TUTOR_RELEVANCE_THRESHOLD
    had_relevant = len(chunks) > 0 and chunks[0].distance < threshold

    context_parts = []
    sources = []
    for chunk in chunks:
        context_parts.append(
            f"[Source: {chunk.source_title}]\n{chunk.text}"
        )
        sources.append({
            "source_type": chunk.source_type,
            "source_id": chunk.source_id,
            "title": chunk.source_title,
            "chunk_index": chunk.chunk_index,
        })

    context_text = "\n---\n".join(context_parts) if context_parts else "(No course materials found)"

    user_prompt = (
        f"Course material excerpts:\n---\n{context_text}\n---\n\n"
        f"Student's question: {question}"
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=settings.RAG_TUTOR_LLM_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    answer = response.content[0].text.strip()

    ChatMessage.objects.create(
        subject_id=subject_id,
        student=student,
        question=question,
        answer=answer,
        sources=sources,
        had_relevant_chunks=had_relevant,
    )

    return {
        "answer": answer,
        "sources": sources,
        "had_relevant_chunks": had_relevant,
    }
