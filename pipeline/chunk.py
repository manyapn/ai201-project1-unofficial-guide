def chunk_text(text, chunk_size=400, overlap=50, metadata=None):
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append({
            "text": chunk,
            "metadata": {**(metadata or {}), "chunk_index": len(chunks)}
        })
        start += chunk_size - overlap

    return chunks
