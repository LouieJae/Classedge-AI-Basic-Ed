import re


def chunk_text(text, max_tokens=500, overlap_tokens=50):
    text = text.strip()
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if current_len + sentence_len > max_chars and current_chunk:
            chunks.append(" ".join(current_chunk))

            overlap_chunk = []
            overlap_len = 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) > overlap_chars:
                    break
                overlap_chunk.insert(0, s)
                overlap_len += len(s) + 1

            current_chunk = overlap_chunk + [sentence]
            current_len = sum(len(s) for s in current_chunk) + len(current_chunk) - 1
        else:
            current_chunk.append(sentence)
            current_len += sentence_len + (1 if current_len > 0 else 0)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
