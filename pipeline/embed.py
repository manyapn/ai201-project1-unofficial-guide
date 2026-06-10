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
