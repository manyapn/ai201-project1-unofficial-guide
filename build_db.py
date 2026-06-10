from pipeline.ingest import fetch_cornell_courses, scrape_cureviews, fetch_rmp_professors, load_local_docs, SEMESTERS
from pipeline.chunk import chunk_text
from pipeline.embed import embed_and_store, CHROMA_PATH

DEFAULT_SEMESTERS = SEMESTERS

DOCUMENTS_DIR = "documents"


def build(course_numbers=None, semesters=None, include_rmp=True, chroma_path=CHROMA_PATH, reset=True):
    if semesters is None:
        semesters = DEFAULT_SEMESTERS

    print("Loading local requirement docs...")
    local_docs = load_local_docs(DOCUMENTS_DIR)
    print(f"  {len(local_docs)} docs loaded")

    print("Fetching Cornell Classes API...")
    cornell_docs = fetch_cornell_courses(semesters=semesters)
    print(f"  {len(cornell_docs)} course docs fetched")

    if course_numbers is None:
        all_numbers = list({
            doc["metadata"]["course_number"].replace("CS ", "")
            for doc in cornell_docs
        })
    else:
        all_numbers = course_numbers

    print(f"Scraping CUReviews for {len(all_numbers)} courses...")
    cureviews_docs = scrape_cureviews(all_numbers)
    print(f"  {len(cureviews_docs)} docs scraped")

    if include_rmp:
        print("Fetching RateMyProfessors...")
        rmp_docs = fetch_rmp_professors()
        print(f"  {len(rmp_docs)} professor review docs fetched")
    else:
        rmp_docs = []

    all_docs = local_docs + cornell_docs + cureviews_docs + rmp_docs
    print(f"\nTotal docs: {len(all_docs)}")

    print("Chunking...")
    chunks = []
    for doc in all_docs:
        chunks.extend(chunk_text(doc["text"], metadata=doc["metadata"]))
    print(f"  {len(chunks)} chunks created")

    print("Embedding and storing in ChromaDB...")
    count = embed_and_store(chunks, chroma_path=chroma_path, reset=reset)
    print(f"  {count} chunks stored\n")

    print("Sample chunks:")
    for chunk in chunks[:5]:
        preview = chunk["text"][:120].replace("\n", " ")
        doc_type = chunk["metadata"].get("doc_type", "?")
        source = chunk["metadata"].get("source", "?")
        print(f"  [{doc_type} | {source}] {preview}...")

    return count


if __name__ == "__main__":
    build()
