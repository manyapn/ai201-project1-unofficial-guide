import pytest
from unittest.mock import patch, Mock
from pipeline.ingest import fetch_cornell_courses

# ── Mock data ────────────────────────────────────────────────────────────────

FAKE_COURSE = {
    "subject": "CS",
    "catalogNbr": "3110",
    "titleLong": "Data Structures and Functional Programming",
    "description": "Introduction to functional programming and data structures.",
    "catalogPrereqCoreq": "CS 2110 or CS 2112.",
    "enrollGroups": [
        {
            "classSections": [
                {
                    "meetings": [
                        {
                            "instructors": [
                                {"firstName": "Nate", "lastName": "Foster"}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}

FAKE_RESPONSE = {
    "status": "success",
    "data": {"classes": [FAKE_COURSE]}
}


def make_mock_response(json_data, status_code=200):
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


# ── Unit tests (mocked) ───────────────────────────────────────────────────────

@patch("pipeline.ingest.requests.get")
def test_returns_list(mock_get):
    mock_get.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_cornell_courses(semesters=["FA26"])
    assert isinstance(result, list)


@patch("pipeline.ingest.requests.get")
def test_text_includes_course_number_and_title(mock_get):
    mock_get.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_cornell_courses(semesters=["FA26"])
    assert "CS 3110" in result[0]["text"]
    assert "Data Structures and Functional Programming" in result[0]["text"]


@patch("pipeline.ingest.requests.get")
def test_metadata_required_fields(mock_get):
    mock_get.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_cornell_courses(semesters=["FA26"])
    meta = result[0]["metadata"]
    assert meta["source"] == "cornell_classes_api"
    assert meta["doc_type"] == "course"
    assert meta["course_number"] == "CS 3110"
    assert meta["semester"] == "FA26"
    assert "instructors" in meta
    assert "is_current" in meta


@patch("pipeline.ingest.requests.get")
def test_is_current_true_for_fa26(mock_get):
    mock_get.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_cornell_courses(semesters=["FA26"])
    assert result[0]["metadata"]["is_current"] is True


@patch("pipeline.ingest.requests.get")
def test_is_current_false_for_older_semester(mock_get):
    mock_get.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_cornell_courses(semesters=["FA25"])
    assert result[0]["metadata"]["is_current"] is False


@patch("pipeline.ingest.requests.get")
def test_multiple_semesters_both_fetched(mock_get):
    mock_get.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_cornell_courses(semesters=["FA26", "FA25"])
    semesters = [r["metadata"]["semester"] for r in result]
    assert "FA26" in semesters
    assert "FA25" in semesters


@patch("pipeline.ingest.requests.get")
def test_failed_request_is_skipped(mock_get):
    mock_get.return_value = make_mock_response({}, status_code=500)
    result = fetch_cornell_courses(semesters=["FA26"])
    assert result == []


@patch("pipeline.ingest.requests.get")
def test_instructor_in_metadata(mock_get):
    mock_get.return_value = make_mock_response(FAKE_RESPONSE)
    result = fetch_cornell_courses(semesters=["FA26"])
    assert "Nate Foster" in result[0]["metadata"]["instructors"]


# ── Integration tests (real API) ──────────────────────────────────────────────

@pytest.mark.integration
def test_real_api_returns_cs_courses():
    result = fetch_cornell_courses(subject="CS", semesters=["FA26"])
    assert len(result) > 0, "FA26 returned no CS courses"


@pytest.mark.integration
def test_real_api_course_numbers_are_cs():
    result = fetch_cornell_courses(subject="CS", semesters=["FA26"])
    for doc in result:
        assert doc["metadata"]["course_number"].startswith("CS"), (
            f"Expected CS course, got {doc['metadata']['course_number']}"
        )


@pytest.mark.integration
def test_real_api_text_is_nonempty():
    result = fetch_cornell_courses(subject="CS", semesters=["FA26"])
    for doc in result:
        assert doc["text"].strip() != "", "A course has empty text"


@pytest.mark.integration
def test_real_api_fa26_is_current():
    result = fetch_cornell_courses(subject="CS", semesters=["FA26"])
    for doc in result:
        assert doc["metadata"]["is_current"] is True


@pytest.mark.integration
def test_real_api_fa25_is_not_current():
    result = fetch_cornell_courses(subject="CS", semesters=["FA25"])
    for doc in result:
        assert doc["metadata"]["is_current"] is False


@pytest.mark.integration
def test_real_api_includes_known_course():
    result = fetch_cornell_courses(subject="CS", semesters=["FA26"])
    course_numbers = [doc["metadata"]["course_number"] for doc in result]
    assert "CS 4820" in course_numbers, "CS 4820 (Algorithms) not found in FA26"
