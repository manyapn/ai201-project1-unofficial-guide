import pytest
from pipeline.embed import retrieve


# All tests here are integration tests - they run real ingestion and embed
# into a tmp ChromaDB so they never touch the production chroma_db/

@pytest.mark.integration
def test_build_returns_positive_chunk_count(tmp_path):
    from build_db import build
    count = build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    assert count > 0


@pytest.mark.integration
def test_build_populates_chromadb(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve("CS 3110 workload", k=3, chroma_path=str(tmp_path))
    assert len(results) > 0


@pytest.mark.integration
def test_build_includes_review_docs(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve("CS 3110 workload", k=5, chroma_path=str(tmp_path))
    doc_types = [r["metadata"].get("doc_type") for r in results]
    assert "review" in doc_types


@pytest.mark.integration
def test_build_includes_schedule_doc(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve("is CS 3110 offered in the fall?", k=5, chroma_path=str(tmp_path))
    texts = " ".join(r["text"] for r in results)
    assert "FA" in texts or "fall" in texts.lower()


@pytest.mark.integration
def test_build_semester_history_has_professor(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve("who taught CS 3110 last fall?", k=5, chroma_path=str(tmp_path))
    texts = " ".join(r["text"] for r in results)
    known_profs = ["Mohan", "Foster", "Clarkson", "Kozen"]
    assert any(p in texts for p in known_profs)


@pytest.mark.integration
def test_build_includes_requirement_docs(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve("what grades do I need to affiliate with CS?", k=5, chroma_path=str(tmp_path))
    texts = " ".join(r["text"] for r in results)
    assert "2.50" in texts or "affiliate" in texts.lower() or "C" in texts


@pytest.mark.integration
def test_build_includes_course_metadata_docs(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve("CS 3110 prerequisites", k=5, chroma_path=str(tmp_path),
                       filters={"doc_type": "course"})
    assert len(results) > 0
    assert all(r["metadata"]["doc_type"] == "course" for r in results)


@pytest.mark.integration
def test_build_no_none_in_metadata(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve("CS 3110", k=5, chroma_path=str(tmp_path))
    for r in results:
        for v in r["metadata"].values():
            assert v is not None, f"None found in metadata: {r['metadata']}"


@pytest.mark.integration
def test_build_rmp_reviews_included(tmp_path):
    from build_db import build
    build(
        course_numbers=[],
        semesters=["FA26"],
        include_rmp=True,
        chroma_path=str(tmp_path)
    )
    results = retrieve("Professor Clarkson teaching style", k=5, chroma_path=str(tmp_path))
    sources = [r["metadata"].get("source") for r in results]
    assert "ratemyprofessors" in sources


@pytest.mark.integration
def test_build_is_current_filter_works(tmp_path):
    from build_db import build
    build(
        course_numbers=["3110"],
        semesters=["FA26", "FA25"],
        include_rmp=False,
        chroma_path=str(tmp_path)
    )
    results = retrieve(
        "CS 3110",
        k=5,
        chroma_path=str(tmp_path),
        filters={"is_current": True}
    )
    for r in results:
        if "is_current" in r["metadata"]:
            assert r["metadata"]["is_current"] is True
