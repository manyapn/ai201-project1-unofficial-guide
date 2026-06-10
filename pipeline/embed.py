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


def retrieve(query, k=5, collection_name=COLLECTION_NAME, chroma_path=CHROMA_PATH,
             filters=None, where_document=None):
    model = _get_model()
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(collection_name)

    raw = model.encode([query])
    query_embedding = raw.tolist()[0] if hasattr(raw, "tolist") else raw[0]

    kwargs = {"query_embeddings": [query_embedding], "n_results": k}
    if filters:
        kwargs["where"] = filters
    if where_document:
        kwargs["where_document"] = where_document

    results = collection.query(**kwargs)

    return [
        {
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        }
        for i, doc in enumerate(results["documents"][0])
    ]


_REQUIREMENT_KEYWORDS = {
    "affiliate", "affiliation", "declare", "requirement", "required",
    "degree", "gpa", "average", "credits", "credit"
}

_COURSE_INFER_THRESHOLD = 0.1


def _is_requirement_query(query):
    q = query.lower()
    return any(kw in q for kw in _REQUIREMENT_KEYWORDS)


def _infer_courses_from_query(query, k=3, collection_name=COLLECTION_NAME, chroma_path=CHROMA_PATH):
    """Semantically match query against course descriptions to find relevant course numbers."""
    hits = retrieve(query, k=k, collection_name=collection_name,
                    chroma_path=chroma_path, filters={"doc_type": "course"})
    seen_nums = []
    for hit in hits:
        if (1 - hit["distance"]) >= _COURSE_INFER_THRESHOLD:
            num = hit["metadata"].get("course_number", "").replace("CS ", "")
            if num and num not in seen_nums:
                seen_nums.append(num)
    return seen_nums


def smart_retrieve(query, k=7, collection_name=COLLECTION_NAME, chroma_path=CHROMA_PATH):
    cs_matches = re.findall(r'\bCS\s*(\d{4})\b', query, re.IGNORECASE)
    math_matches = re.findall(r'\bMATH\s*(\d{4})\b', query, re.IGNORECASE)

    # When no explicit course numbers and not a requirement query, infer from course descriptions
    if not cs_matches and not _is_requirement_query(query):
        cs_matches = _infer_courses_from_query(
            query, collection_name=collection_name, chroma_path=chroma_path
        )

    seen = set()
    chunks = []

    def _add(new_chunks, threshold=-0.5):
        for c in new_chunks:
            if c["text"] not in seen and (1 - c["distance"]) >= threshold:
                seen.add(c["text"])
                chunks.append(c)

    if _is_requirement_query(query):
        # requirement query: only requirement docs, keyword-search for each course number
        _add(retrieve(query, k=k, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"doc_type": "requirement"}))
        for num in cs_matches:
            _add(retrieve(query, k=3, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"doc_type": "requirement"},
                          where_document={"$contains": f"CS {num}"}))
        for num in math_matches:
            _add(retrieve(query, k=3, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"doc_type": "requirement"},
                          where_document={"$contains": f"MATH {num}"}))
    elif len(cs_matches) > 1:
        # multi-course comparison: broad semantic + per-course docs for each course
        _add(retrieve(query, k=5, collection_name=collection_name,
                      chroma_path=chroma_path))
        for num in cs_matches:
            course_num = f"CS {num}"
            _add(retrieve(query, k=4, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"course_number": course_num}))
            _add(retrieve(query, k=2, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"doc_type": "requirement"},
                          where_document={"$contains": course_num}))
    elif cs_matches:
        course_num = f"CS {cs_matches[0]}"
        _add(retrieve(query, k=k, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"course_number": course_num}))
        _add(retrieve(query, k=4, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"doc_type": "requirement"},
                      where_document={"$contains": course_num}))
    else:
        # general query: broad semantic search + requirement docs
        _add(retrieve(query, k=k, collection_name=collection_name,
                      chroma_path=chroma_path))
        _add(retrieve(query, k=4, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"doc_type": "requirement"}))

    return chunks
