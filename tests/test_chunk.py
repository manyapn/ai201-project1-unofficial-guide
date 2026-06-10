import pytest
from pipeline.chunk import chunk_text


def test_empty_text_returns_empty():
    assert chunk_text("") == []


def test_short_text_is_one_chunk():
    result = chunk_text("Short review.")
    assert len(result) == 1
    assert result[0]["text"] == "Short review."


def test_chunk_size_respected():
    result = chunk_text("A" * 1000)
    for chunk in result:
        assert len(chunk["text"]) <= 400


def test_overlap_applied():
    result = chunk_text("A" * 1000)
    assert result[0]["text"][-50:] == result[1]["text"][:50]


def test_metadata_attached():
    meta = {"source": "cureviews", "course_number": "CS 3110"}
    result = chunk_text("Some review text here.", metadata=meta)
    assert result[0]["metadata"]["source"] == "cureviews"
    assert result[0]["metadata"]["course_number"] == "CS 3110"
    assert result[0]["metadata"]["chunk_index"] == 0


def test_no_metadata_gives_only_chunk_index():
    result = chunk_text("Some text.")
    assert result[0]["metadata"] == {"chunk_index": 0}


def test_chunk_index_increments():
    result = chunk_text("A" * 1000)
    for i, chunk in enumerate(result):
        assert chunk["metadata"]["chunk_index"] == i
