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

_COURSE_NICKNAMES = [
    (re.compile(r'\bintro(?:duction)?\s+to\s+a\.?i\.?\b', re.IGNORECASE), "3700"),
    (re.compile(r'\bfoundations?\s+of\s+a\.?i\.?\b', re.IGNORECASE), "3700"),
    (re.compile(r'\bintro(?:duction)?\s+to\s+(?:machine\s+learning|m\.?l\.?)\b', re.IGNORECASE), "3780"),
    (re.compile(r'\bfunctional\s+programming\b', re.IGNORECASE), "3110"),
    (re.compile(r'\bdata\s+structures\b', re.IGNORECASE), "2110"),
    (re.compile(r'\balgorithms\b', re.IGNORECASE), "4820"),
    (re.compile(r'\boperating\s+systems\b', re.IGNORECASE), "4410"),
    (re.compile(r'\bdeep\s+learning\b', re.IGNORECASE), "5787"),
    (re.compile(r'\bnatural\s+language\s+processing\b|\bnlp\b', re.IGNORECASE), "4740"),
]


def _is_requirement_query(query):
    q = query.lower()
    return any(kw in q for kw in _REQUIREMENT_KEYWORDS)


def _extract_course_numbers(query):
    explicit = re.findall(r'\bCS\s*(\d{4})\b', query, re.IGNORECASE)
    inferred = []
    for pattern, num in _COURSE_NICKNAMES:
        if pattern.search(query) and num not in explicit and num not in inferred:
            inferred.append(num)
    return explicit, inferred


def smart_retrieve(query, k=7, collection_name=COLLECTION_NAME, chroma_path=CHROMA_PATH):
    cs_matches, inferred = _extract_course_numbers(query)
    math_matches = re.findall(r'\bMATH\s*(\d{4})\b', query, re.IGNORECASE)
    all_cs = cs_matches + inferred

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
        for num in all_cs:
            _add(retrieve(query, k=3, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"doc_type": "requirement"},
                          where_document={"$contains": f"CS {num}"}))
        for num in math_matches:
            _add(retrieve(query, k=3, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"doc_type": "requirement"},
                          where_document={"$contains": f"MATH {num}"}))
    elif len(all_cs) > 1:
        # multi-course comparison: broad semantic + per-course docs for each course
        _add(retrieve(query, k=5, collection_name=collection_name,
                      chroma_path=chroma_path))
        for num in all_cs:
            course_num = f"CS {num}"
            course_num_nospace = f"CS{num}"
            _add(retrieve(query, k=4, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"course_number": course_num}))
            # RMP reviews store course as "CS3110" (no space) in review text
            _add(retrieve(query, k=3, collection_name=collection_name,
                          chroma_path=chroma_path,
                          where_document={"$contains": course_num_nospace}))
            _add(retrieve(query, k=2, collection_name=collection_name,
                          chroma_path=chroma_path,
                          filters={"doc_type": "requirement"},
                          where_document={"$contains": course_num}))
    elif all_cs:
        course_num = f"CS {all_cs[0]}"
        course_num_nospace = f"CS{all_cs[0]}"
        # course-specific query: filter to that course's docs (CUReviews have course_number field)
        _add(retrieve(query, k=k, collection_name=collection_name,
                      chroma_path=chroma_path,
                      filters={"course_number": course_num}))
        # RMP reviews store course as "CS3110" (no space) in review text
        _add(retrieve(query, k=4, collection_name=collection_name,
                      chroma_path=chroma_path,
                      where_document={"$contains": course_num_nospace}))
        # keyword-search requirement docs for this course number
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
