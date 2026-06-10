import pytest
from unittest.mock import patch, Mock
from pipeline.ingest import fetch_rmp_professors

FAKE_CS_PROFESSOR = {
    "node": {
        "id": "abc123",
        "firstName": "Nate",
        "lastName": "Foster",
        "department": "Computer Science",
        "avgRating": 4.2,
        "avgDifficulty": 3.5,
        "numRatings": 45,
        "ratings": {
            "edges": [
                {
                    "node": {
                        "comment": "Great professor, explains concepts clearly.",
                        "clarityRating": 5,
                        "difficultyRating": 3,
                        "helpfulRating": 5,
                        "date": "2025-05-10 00:00:00 +0000 UTC",
                        "class": "CS3110"
                    }
                },
                {
                    "node": {
                        "comment": "Tough grader but very passionate about the material.",
                        "clarityRating": 4,
                        "difficultyRating": 4,
                        "helpfulRating": 4,
                        "date": "2025-01-15 00:00:00 +0000 UTC",
                        "class": "CS3110"
                    }
                }
            ]
        }
    }
}

FAKE_NON_CS_PROFESSOR = {
    "node": {
        "id": "xyz999",
        "firstName": "John",
        "lastName": "Smith",
        "department": "Biology",
        "avgRating": 3.0,
        "avgDifficulty": 2.0,
        "numRatings": 10,
        "ratings": {
            "edges": [
                {
                    "node": {
                        "comment": "Good biology professor.",
                        "clarityRating": 3,
                        "difficultyRating": 2,
                        "helpfulRating": 3,
                        "date": "2025-05-10 00:00:00 +0000 UTC",
                        "class": "BIO1500"
                    }
                }
            ]
        }
    }
}

FAKE_CS_PROFESSOR_EMPTY_COMMENT = {
    "node": {
        "id": "def456",
        "firstName": "Walker",
        "lastName": "White",
        "department": "Computer Science",
        "avgRating": 3.8,
        "avgDifficulty": 3.0,
        "numRatings": 5,
        "ratings": {
            "edges": [
                {
                    "node": {
                        "comment": "",
                        "clarityRating": 3,
                        "difficultyRating": 3,
                        "helpfulRating": 3,
                        "date": "2025-05-10 00:00:00 +0000 UTC",
                        "class": "CS2110"
                    }
                }
            ]
        }
    }
}

FAKE_RESPONSE = {
    "data": {
        "newSearch": {
            "teachers": {
                "edges": [FAKE_CS_PROFESSOR, FAKE_NON_CS_PROFESSOR]
            }
        }
    }
}

FAKE_RESPONSE_EMPTY_COMMENT = {
    "data": {
        "newSearch": {
            "teachers": {
                "edges": [FAKE_CS_PROFESSOR_EMPTY_COMMENT]
            }
        }
    }
}

FAKE_RESPONSE_EMPTY = {
    "data": {
        "newSearch": {
            "teachers": {
                "edges": []
            }
        }
    }
}


def make_mock_response(json_data, status_code=200):
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


# ── Unit tests (mocked) ───────────────────────────────────────────────────────

@patch("pipeline.ingest.requests.post")
def test_returns_list(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_rmp_professors()
    assert isinstance(result, list)


@patch("pipeline.ingest.requests.post")
def test_filters_non_cs_departments(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_rmp_professors()
    for doc in result:
        assert doc["metadata"]["department"] == "Computer Science"


@patch("pipeline.ingest.requests.post")
def test_text_includes_professor_name_and_comment(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_rmp_professors()
    assert "Nate Foster" in result[0]["text"]
    assert "Great professor" in result[0]["text"]


@patch("pipeline.ingest.requests.post")
def test_text_includes_class(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_rmp_professors()
    assert "CS3110" in result[0]["text"]


@patch("pipeline.ingest.requests.post")
def test_empty_comment_is_skipped(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE_EMPTY_COMMENT)
    result = fetch_rmp_professors()
    assert result == []


@patch("pipeline.ingest.requests.post")
def test_metadata_required_fields(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_rmp_professors()
    meta = result[0]["metadata"]
    assert meta["source"] == "ratemyprofessors"
    assert meta["doc_type"] == "review"
    assert meta["professor_name"] == "Nate Foster"
    assert meta["department"] == "Computer Science"
    assert "class" in meta
    assert "clarity_rating" in meta
    assert "difficulty_rating" in meta
    assert "helpful_rating" in meta
    assert "date" in meta
    assert "avg_rating" in meta
    assert "avg_difficulty" in meta


@patch("pipeline.ingest.requests.post")
def test_failed_request_returns_empty(mock_post):
    mock_post.return_value = make_mock_response({}, status_code=500)
    result = fetch_rmp_professors()
    assert result == []


@patch("pipeline.ingest.requests.post")
def test_no_professors_returns_empty(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE_EMPTY)
    result = fetch_rmp_professors()
    assert result == []


@patch("pipeline.ingest.requests.post")
def test_avg_rating_in_metadata(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_rmp_professors()
    assert result[0]["metadata"]["avg_rating"] == 4.2
    assert result[0]["metadata"]["avg_difficulty"] == 3.5


@patch("pipeline.ingest.requests.post")
def test_multiple_reviews_per_professor(mock_post):
    mock_post.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_rmp_professors()
    professor_reviews = [
        doc for doc in result
        if "Nate Foster" in doc["text"]
    ]
    assert len(professor_reviews) == 2


# ── Integration tests (real API) ──────────────────────────────────────────────

@pytest.mark.integration
def test_real_api_returns_cs_professors():
    result = fetch_rmp_professors()
    assert len(result) > 0, "No CS professor reviews returned"


@pytest.mark.integration
def test_real_api_all_docs_are_cs_department():
    result = fetch_rmp_professors()
    for doc in result:
        assert doc["metadata"]["department"] == "Computer Science"


@pytest.mark.integration
def test_real_api_reviews_have_nonempty_text():
    result = fetch_rmp_professors()
    for doc in result:
        assert doc["text"].strip() != ""


@pytest.mark.integration
def test_real_api_known_professor_present():
    result = fetch_rmp_professors()
    names = [doc["metadata"]["professor_name"] for doc in result]
    assert any("Clarkson" in name for name in names), "Michael Clarkson not found in results"


@pytest.mark.integration
def test_real_api_ratings_are_numeric_or_none():
    result = fetch_rmp_professors()
    for doc in result:
        for field in ("clarity_rating", "difficulty_rating", "helpful_rating"):
            val = doc["metadata"][field]
            assert val is None or isinstance(val, (int, float)), (
                f"{field} should be numeric or None, got {val}"
            )


@pytest.mark.integration
def test_real_api_metadata_fields_present():
    result = fetch_rmp_professors()
    for doc in result:
        meta = doc["metadata"]
        assert meta["source"] == "ratemyprofessors"
        assert meta["doc_type"] == "review"
        assert "professor_name" in meta
        assert "avg_rating" in meta
        assert "avg_difficulty" in meta
