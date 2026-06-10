import pytest
from pipeline.ingest import load_local_docs


def test_loads_txt_files(tmp_path):
    (tmp_path / "test.txt").write_text("Hello world")
    result = load_local_docs(str(tmp_path))
    assert len(result) == 1
    assert result[0]["text"] == "Hello world"
    assert result[0]["metadata"]["source"] == "test.txt"


def test_ignores_non_txt(tmp_path):
    (tmp_path / "ignore.md").write_text("Not a txt file")
    result = load_local_docs(str(tmp_path))
    assert result == []


def test_empty_directory(tmp_path):
    result = load_local_docs(str(tmp_path))
    assert result == []


def test_doc_type_is_requirement(tmp_path):
    (tmp_path / "affiliation_eng.txt").write_text("Some requirement text.")
    result = load_local_docs(str(tmp_path))
    assert result[0]["metadata"]["doc_type"] == "requirement"


def test_multiple_files(tmp_path):
    (tmp_path / "a.txt").write_text("Doc A")
    (tmp_path / "b.txt").write_text("Doc B")
    result = load_local_docs(str(tmp_path))
    assert len(result) == 2
