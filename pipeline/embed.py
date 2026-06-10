import re
import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "cornell_cs"

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def sanitize_metadata(metadata):
    return {k: ("" if v is None else v) for k, v in metadata.items()}


def embed_and_store(chunks, collection_name=COLLECTION_NAME, chroma_path=CHROMA_PATH, reset=True):
    if not chunks:
        return 0

    model = _get_model()
    client = chromadb.PersistentClient(path=chroma_path)

    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(collection_name)

    texts = [c["text"] for c in chunks]
    metadatas = [sanitize_metadata(c["metadata"]) for c in chunks]
    raw = model.encode(texts, show_progress_bar=True)
    embeddings = raw.tolist() if hasattr(raw, "tolist") else raw
    ids = [str(i) for i in range(len(chunks))]

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        collection.add(
            ids=ids[i:i + batch_size],
            embeddings=embeddings[i:i + batch_size],
            documents=texts[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size]
        )

    return len(chunks)


def retrieve(query, k=5, collection_name=COLLECTION_NAME, chroma_path=CHROMA_PATH, filters=None):
    model = _get_model()
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(collection_name)

    raw = model.encode([query])
    query_embedding = raw.tolist()[0] if hasattr(raw, "tolist") else raw[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=filters
    )

    return [
        {
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        }
        for i, doc in enumerate(results["documents"][0])
    ]


def smart_retrieve(query, k=7, collection_name=COLLECTION_NAME, chroma_path=CHROMA_PATH):
    """Retrieval that detects course numbers and mixes in requirement docs.

    When the query names a specific course (e.g. 'CS 3110'), it filters
    retrieval to that course's documents so reviews from other courses don't
    crowd out the answer. It always appends a requirement-doc pass so
    policy questions (required courses, practicum lists) surface correctly.
    Results are deduplicated by text so the same chunk from multiple semesters
    only appears once.
    """
    match = re.search(r'\bCS\s*(\d{4})\b', query, re.IGNORECASE)

    seen = set()
    chunks = []

    def _add(new_chunks):
        for c in new_chunks:
            if c["text"] not in seen:
                seen.add(c["text"])
                chunks.append(c)

    if match:
        course_num = f"CS {match.group(1)}"
        _add(retrieve(query, k=k, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"course_number": course_num}))
        _add(retrieve(query, k=4, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"doc_type": "requirement"}))
    else:
        _add(retrieve(query, k=k, collection_name=collection_name,
                      chroma_path=chroma_path))
        _add(retrieve(query, k=4, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"doc_type": "requirement"}))

    return chunks
