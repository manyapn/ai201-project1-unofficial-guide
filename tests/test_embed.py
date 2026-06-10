import pytest
from unittest.mock import patch, MagicMock
from pipeline.embed import sanitize_metadata, embed_and_store, retrieve

FAKE_CHUNKS = [
    {
        "text": "CS 3110 is a challenging but rewarding course on functional programming.",
        "metadata": {"source": "cureviews", "course_number": "CS 3110", "doc_type": "review", "rating": 4}
    },
    {
        "text": "Professor Foster is excellent and very passionate about the material.",
        "metadata": {"source": "ratemyprofessors", "professor_name": "Nate Foster", "doc_type": "review", "rating": None}
    },
    {
        "text": "CS 3110 (Data Structures) semester history. Fall semesters offered: FA22, FA23, FA24, FA25. Spring semesters offered: SP23, SP24. Professors by semester: FA23: Nate Foster. SP24: Anshuman Mohan.",
        "metadata": {"source": "cureviews", "course_number": "CS 3110", "doc_type": "course_schedule", "rating": None}
    },
]


# ── sanitize_metadata ─────────────────────────────────────────────────────────

def test_sanitize_none_becomes_empty_string():
    meta = {"rating": None, "source": "cureviews"}
    result = sanitize_metadata(meta)
    assert result["rating"] == ""


def test_sanitize_preserves_strings():
    meta = {"source": "cureviews", "course_number": "CS 3110"}
    result = sanitize_metadata(meta)
    assert result["source"] == "cureviews"
    assert result["course_number"] == "CS 3110"


def test_sanitize_preserves_numbers():
    meta = {"rating": 4.5, "is_current": True}
    result = sanitize_metadata(meta)
    assert result["rating"] == 4.5
    assert result["is_current"] is True


def test_sanitize_empty_metadata():
    assert sanitize_metadata({}) == {}


def test_sanitize_all_none():
    meta = {"a": None, "b": None}
    result = sanitize_metadata(meta)
    assert result == {"a": "", "b": ""}


# ── embed_and_store (mocked) ──────────────────────────────────────────────────

def make_mock_encoder(n):
    mock = MagicMock()
    mock.encode.return_value = [[0.1] * 384] * n
    return mock


@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_embed_and_store_returns_chunk_count(mock_model_cls, mock_client_cls):
    mock_model_cls.return_value = make_mock_encoder(len(FAKE_CHUNKS))
    mock_collection = MagicMock()
    mock_client_cls.return_value.get_or_create_collection.return_value = mock_collection
    result = embed_and_store(FAKE_CHUNKS)
    assert result == len(FAKE_CHUNKS)


@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_embed_and_store_calls_add(mock_model_cls, mock_client_cls):
    mock_model_cls.return_value = make_mock_encoder(len(FAKE_CHUNKS))
    mock_collection = MagicMock()
    mock_client_cls.return_value.get_or_create_collection.return_value = mock_collection
    embed_and_store(FAKE_CHUNKS)
    assert mock_collection.add.called


@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_embed_and_store_reset_deletes_collection(mock_model_cls, mock_client_cls):
    mock_model_cls.return_value = make_mock_encoder(len(FAKE_CHUNKS))
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = MagicMock()
    mock_client_cls.return_value = mock_client
    embed_and_store(FAKE_CHUNKS, reset=True)
    mock_client.delete_collection.assert_called_once()


@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_embed_and_store_no_reset_skips_delete(mock_model_cls, mock_client_cls):
    mock_model_cls.return_value = make_mock_encoder(len(FAKE_CHUNKS))
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = MagicMock()
    mock_client_cls.return_value = mock_client
    embed_and_store(FAKE_CHUNKS, reset=False)
    mock_client.delete_collection.assert_not_called()


@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_embed_and_store_empty_chunks(mock_model_cls, mock_client_cls):
    mock_model_cls.return_value = make_mock_encoder(0)
    mock_client_cls.return_value.get_or_create_collection.return_value = MagicMock()
    result = embed_and_store([])
    assert result == 0


# ── retrieve (mocked) ─────────────────────────────────────────────────────────

@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_retrieve_returns_list(mock_model_cls, mock_client_cls):
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1] * 384]
    mock_model_cls.return_value = mock_model

    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["some text"]],
        "metadatas": [[{"source": "cureviews"}]],
        "distances": [[0.1]]
    }
    mock_client_cls.return_value.get_or_create_collection.return_value = mock_collection

    result = retrieve("test query", k=1)
    assert isinstance(result, list)
    assert len(result) == 1


@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_retrieve_result_has_text_metadata_distance(mock_model_cls, mock_client_cls):
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1] * 384]
    mock_model_cls.return_value = mock_model

    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["some text"]],
        "metadatas": [[{"source": "cureviews"}]],
        "distances": [[0.25]]
    }
    mock_client_cls.return_value.get_or_create_collection.return_value = mock_collection

    result = retrieve("test query", k=1)
    assert result[0]["text"] == "some text"
    assert result[0]["metadata"]["source"] == "cureviews"
    assert result[0]["distance"] == 0.25


@patch("pipeline.embed.chromadb.PersistentClient")
@patch("pipeline.embed.SentenceTransformer")
def test_retrieve_passes_filters(mock_model_cls, mock_client_cls):
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1] * 384]
    mock_model_cls.return_value = mock_model

    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [[]], "metadatas": [[]], "distances": [[]]
    }
    mock_client_cls.return_value.get_or_create_collection.return_value = mock_collection

    retrieve("query", k=3, filters={"source": "cureviews"})
    call_kwargs = mock_collection.query.call_args[1]
    assert call_kwargs["where"] == {"source": "cureviews"}


# ── Integration tests (real model + real ChromaDB) ────────────────────────────

@pytest.mark.integration
def test_real_embed_and_store_returns_count(tmp_path):
    result = embed_and_store(FAKE_CHUNKS, chroma_path=str(tmp_path))
    assert result == len(FAKE_CHUNKS)


@pytest.mark.integration
def test_real_retrieve_returns_k_results(tmp_path):
    embed_and_store(FAKE_CHUNKS, chroma_path=str(tmp_path))
    results = retrieve("functional programming course", k=2, chroma_path=str(tmp_path))
    assert len(results) == 2


@pytest.mark.integration
def test_real_retrieve_has_text_metadata_distance(tmp_path):
    embed_and_store(FAKE_CHUNKS, chroma_path=str(tmp_path))
    results = retrieve("professor review", k=1, chroma_path=str(tmp_path))
    assert "text" in results[0]
    assert "metadata" in results[0]
    assert "distance" in results[0]


@pytest.mark.integration
def test_real_retrieve_semester_history_question(tmp_path):
    embed_and_store(FAKE_CHUNKS, chroma_path=str(tmp_path))
    results = retrieve("is CS 3110 offered in the fall?", k=2, chroma_path=str(tmp_path))
    texts = " ".join(r["text"] for r in results)
    assert "FA" in texts or "fall" in texts.lower()


@pytest.mark.integration
def test_real_retrieve_filter_by_source(tmp_path):
    embed_and_store(FAKE_CHUNKS, chroma_path=str(tmp_path))
    results = retrieve("course review", k=3, chroma_path=str(tmp_path), filters={"source": "cureviews"})
    for r in results:
        assert r["metadata"]["source"] == "cureviews"


@pytest.mark.integration
def test_real_metadata_none_sanitized(tmp_path):
    embed_and_store(FAKE_CHUNKS, chroma_path=str(tmp_path))
    results = retrieve("professor", k=3, chroma_path=str(tmp_path))
    for r in results:
        for v in r["metadata"].values():
            assert v is not None
