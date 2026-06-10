import pytest
from unittest.mock import patch, Mock
from pipeline.ingest import scrape_cureviews

FAKE_COURSE_INFO = {
    "result": {
        "_id": "abc123",
        "classTitle": "Data Structures and Functional Programming",
        "classDifficulty": 3.5,
        "classRating": 4.3,
        "classWorkload": 3.7,
        "classProfessors": ["Nate Foster"],
        "classSems": ["FA22", "SP23", "FA23", "SP24", "FA24", "SP25", "FA25", "SP26"]
    }
}

FAKE_REVIEWS = {
    "result": [
        {
            "text": "Great course, very challenging but worth it.",
            "rating": 4,
            "difficulty": 4,
            "workload": 4,
            "professors": ["Nate Foster"],
            "date": "2023-12-10T00:00:00.000Z"   # FA23
        },
        {
            "text": "OCaml is tough but the professor is excellent.",
            "rating": 5,
            "difficulty": 3,
            "workload": 3,
            "professors": ["Anshuman Mohan"],
            "date": "2025-05-10T00:00:00.000Z"   # SP25
        },
        {
            "text": "",
            "rating": 3,
            "difficulty": 3,
            "workload": 3,
            "professors": ["Anshuman Mohan"],
            "date": "2025-05-12T00:00:00.000Z"   # SP25, empty - should be skipped
        }
    ]
}

FAKE_COURSE_INFO_NO_RESULT = {"result": None}
FAKE_REVIEWS_EMPTY = {"result": []}


def make_mock_response(json_data, status_code=200):
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


# ── Unit tests (mocked) ───────────────────────────────────────────────────────

@patch("pipeline.ingest.requests.post")
def test_returns_list(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    assert isinstance(result, list)


@patch("pipeline.ingest.requests.post")
def test_text_includes_course_number_and_review(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    review_docs = [d for d in result if d["metadata"]["doc_type"] == "review"]
    assert "CS 3110" in review_docs[0]["text"]
    assert "Great course" in review_docs[0]["text"]


@patch("pipeline.ingest.requests.post")
def test_empty_review_text_is_skipped(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    for doc in result:
        assert doc["text"].strip() != ""


@patch("pipeline.ingest.requests.post")
def test_metadata_required_fields(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    review_docs = [d for d in result if d["metadata"]["doc_type"] == "review"]
    meta = review_docs[0]["metadata"]
    assert meta["source"] == "cureviews"
    assert meta["doc_type"] == "review"
    assert meta["course_number"] == "CS 3110"
    assert "professor" in meta
    assert "rating" in meta
    assert "difficulty" in meta
    assert "workload" in meta
    assert "date" in meta


@patch("pipeline.ingest.requests.post")
def test_professor_in_metadata(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    review_docs = [d for d in result if d["metadata"]["doc_type"] == "review"]
    professors = [d["metadata"]["professor"] for d in review_docs]
    assert any("Nate Foster" in p for p in professors)


@patch("pipeline.ingest.requests.post")
def test_failed_course_info_request_is_skipped(mock_post):
    mock_post.return_value = make_mock_response({}, status_code=500)
    result = scrape_cureviews(["3110"])
    assert result == []


@patch("pipeline.ingest.requests.post")
def test_missing_course_result_is_skipped(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO_NO_RESULT),
    ]
    result = scrape_cureviews(["3110"])
    assert result == []


@patch("pipeline.ingest.requests.post")
def test_failed_reviews_request_is_skipped(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response({}, status_code=500)
    ]
    result = scrape_cureviews(["3110"])
    assert result == []


@patch("pipeline.ingest.requests.post")
def test_no_reviews_returns_only_schedule_doc(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS_EMPTY)
    ]
    result = scrape_cureviews(["3110"])
    review_docs = [d for d in result if d["metadata"]["doc_type"] == "review"]
    assert len(review_docs) == 0


@patch("pipeline.ingest.requests.post")
def test_multiple_courses_both_fetched(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS),
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110", "4820"])
    course_numbers = [doc["metadata"]["course_number"] for doc in result]
    assert "CS 3110" in course_numbers
    assert "CS 4820" in course_numbers


# ── Integration tests (real API) ──────────────────────────────────────────────

@pytest.mark.integration
def test_real_api_returns_reviews_for_cs3110():
    result = scrape_cureviews(["3110"])
    assert len(result) > 0, "No reviews returned for CS 3110"


@pytest.mark.integration
def test_real_api_reviews_have_nonempty_text():
    result = scrape_cureviews(["3110"])
    for doc in result:
        assert doc["text"].strip() != "", "A review has empty text"


@pytest.mark.integration
def test_real_api_course_number_in_text():
    result = scrape_cureviews(["3110"])
    for doc in result:
        assert "CS 3110" in doc["text"]


@pytest.mark.integration
def test_real_api_metadata_fields_present():
    result = scrape_cureviews(["3110"])
    review_docs = [d for d in result if d["metadata"]["doc_type"] == "review"]
    for doc in review_docs:
        meta = doc["metadata"]
        assert meta["source"] == "cureviews"
        assert meta["doc_type"] == "review"
        assert meta["course_number"] == "CS 3110"
        assert "professor" in meta
        assert "rating" in meta


@pytest.mark.integration
def test_real_api_ratings_are_numeric_or_none():
    result = scrape_cureviews(["3110"])
    review_docs = [d for d in result if d["metadata"]["doc_type"] == "review"]
    for doc in review_docs:
        for field in ("rating", "difficulty", "workload"):
            val = doc["metadata"][field]
            assert val is None or isinstance(val, (int, float)), (
                f"{field} should be numeric or None, got {val}"
            )


@pytest.mark.integration
def test_real_api_known_second_course():
    result = scrape_cureviews(["4820"])
    assert len(result) > 0, "No reviews returned for CS 4820"
    for doc in result:
        assert "CS 4820" in doc["text"]


# ── Semester history tests (mocked) ──────────────────────────────────────────

@patch("pipeline.ingest.requests.post")
def test_semester_history_doc_created(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_docs = [d for d in result if d["metadata"]["doc_type"] == "course_schedule"]
    assert len(schedule_docs) == 1


@patch("pipeline.ingest.requests.post")
def test_semester_history_text_has_fall_and_spring(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    assert "Fall" in schedule_doc["text"]
    assert "Spring" in schedule_doc["text"]


@patch("pipeline.ingest.requests.post")
def test_semester_history_text_has_course_number(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    assert "CS 3110" in schedule_doc["text"]


@patch("pipeline.ingest.requests.post")
def test_semester_history_separates_fall_correctly(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    assert "FA22" in schedule_doc["text"]
    assert "FA23" in schedule_doc["text"]


@patch("pipeline.ingest.requests.post")
def test_semester_history_separates_spring_correctly(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    assert "SP23" in schedule_doc["text"]
    assert "SP26" in schedule_doc["text"]


@patch("pipeline.ingest.requests.post")
def test_semester_history_metadata_fields(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    assert schedule_doc["metadata"]["source"] == "cureviews"
    assert schedule_doc["metadata"]["course_number"] == "CS 3110"


@patch("pipeline.ingest.requests.post")
def test_no_sems_still_creates_schedule_doc(mock_post):
    course_no_sems = {
        "result": {
            "_id": "abc123",
            "classTitle": "Data Structures and Functional Programming",
            "classDifficulty": 3.5,
            "classRating": 4.3,
            "classWorkload": 3.7,
            "classProfessors": ["Nate Foster"],
            "classSems": []
        }
    }
    mock_post.side_effect = [
        make_mock_response(course_no_sems),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_docs = [d for d in result if d["metadata"]["doc_type"] == "course_schedule"]
    assert len(schedule_docs) == 1


# ── Professor-semester association tests (mocked) ─────────────────────────────

@patch("pipeline.ingest.requests.post")
def test_prof_semester_map_in_schedule_doc(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    # FA23 review by Nate Foster, SP25 review by Anshuman Mohan
    assert "Nate Foster" in schedule_doc["text"]
    assert "Anshuman Mohan" in schedule_doc["text"]


@patch("pipeline.ingest.requests.post")
def test_prof_semester_infers_fa_from_december_date(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    # December 2023 -> FA23, review was by Nate Foster
    # The professor section comes after "Professors by semester"
    text = schedule_doc["text"]
    prof_section = text.split("Professors by semester")[1] if "Professors by semester" in text else ""
    assert "FA23" in prof_section
    assert "Nate Foster" in prof_section


@patch("pipeline.ingest.requests.post")
def test_prof_semester_infers_sp_from_may_date(mock_post):
    mock_post.side_effect = [
        make_mock_response(FAKE_COURSE_INFO),
        make_mock_response(FAKE_REVIEWS)
    ]
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    # May 2025 -> SP25, review was by Anshuman Mohan
    text = schedule_doc["text"]
    prof_section = text.split("Professors by semester")[1] if "Professors by semester" in text else ""
    assert "SP25" in prof_section
    assert "Anshuman Mohan" in prof_section


# ── Semester history integration tests ───────────────────────────────────────

@pytest.mark.integration
def test_real_api_semester_history_doc_exists():
    result = scrape_cureviews(["3110"])
    schedule_docs = [d for d in result if d["metadata"]["doc_type"] == "course_schedule"]
    assert len(schedule_docs) == 1


@pytest.mark.integration
def test_real_api_semester_history_has_fall_and_spring():
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    assert "Fall" in schedule_doc["text"]
    assert "Spring" in schedule_doc["text"]


@pytest.mark.integration
def test_real_api_semester_history_includes_professors():
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    # CS 3110 has known professors - at least one should appear
    known_profs = ["Mohan", "Foster", "Clarkson", "Kozen"]
    assert any(p in schedule_doc["text"] for p in known_profs), (
        f"No known professor found in schedule doc: {schedule_doc['text'][:300]}"
    )


@pytest.mark.integration
def test_real_api_prof_semester_lines_in_schedule():
    result = scrape_cureviews(["3110"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    # Should have lines like "FA25: Anshuman Mohan"
    assert any(
        sem in schedule_doc["text"]
        for sem in ["FA25", "SP25", "FA24", "SP24"]
    )


@pytest.mark.integration
def test_real_api_cs4780_semester_history():
    result = scrape_cureviews(["4780"])
    schedule_docs = [d for d in result if d["metadata"]["doc_type"] == "course_schedule"]
    assert len(schedule_docs) == 1
    text = schedule_docs[0]["text"]
    assert "CS 4780" in text
    assert "FA" in text or "SP" in text


@pytest.mark.integration
def test_real_api_cs4780_prof_semester_association():
    result = scrape_cureviews(["4780"])
    schedule_doc = next(d for d in result if d["metadata"]["doc_type"] == "course_schedule")
    # CS 4780 has known professors
    known_profs = ["Weinberger", "Benson", "Sridharan", "Haghtalab"]
    assert any(p in schedule_doc["text"] for p in known_profs), (
        f"No known professor found: {schedule_doc['text'][:300]}"
    )
