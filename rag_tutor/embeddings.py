import os

import openai
from django.conf import settings


def embed_texts(texts):
    if not texts:
        return []

    api_key = os.environ.get("OPENAI_API_KEY", "")
    client = openai.OpenAI(api_key=api_key)

    response = client.embeddings.create(
        model=settings.RAG_TUTOR_EMBEDDING_MODEL,
        input=texts,
    )

    return [item.embedding for item in response.data]
