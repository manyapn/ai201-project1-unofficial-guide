import pytest
from unittest.mock import patch, MagicMock
from pipeline.generate import generate

FAKE_CHUNKS = [
    {
        "text": "CS 3110 (Data Structures) semester history. Fall semesters offered: FA22, FA23, FA24, FA25.",
        "metadata": {"source": "cureviews", "doc_type": "course_schedule", "course_number": "CS 3110"}
    },
    {
        "text": "CS 3110: Data Structures and Functional Programming. Introduces functional programming and data structures using OCaml.",
        "metadata": {"source": "cornell_classes_api", "doc_type": "course", "course_number": "CS 3110", "semester": "FA26"}
    }
]


def make_mock_groq_response(content="CS 3110 is offered in the fall."):
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ── Unit tests (mocked) ───────────────────────────────────────────────────────

@patch("pipeline.generate.Groq")
def test_generate_returns_string(mock_groq_cls):
    mock_groq_cls.return_value.chat.completions.create.return_value = make_mock_groq_response()
    result = generate("Is CS 3110 offered in the fall?", FAKE_CHUNKS)
    assert isinstance(result, str)
    assert len(result) > 0


@patch("pipeline.generate.Groq")
def test_generate_calls_groq_with_context(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_response()
    mock_groq_cls.return_value = mock_client

    generate("Is CS 3110 offered in the fall?", FAKE_CHUNKS)

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args[1]["messages"]
    full_text = " ".join(m["content"] for m in messages)
    # chunk text should appear in the prompt
    assert "FA22" in full_text or "FA25" in full_text


@patch("pipeline.generate.Groq")
def test_generate_includes_query_in_prompt(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_response()
    mock_groq_cls.return_value = mock_client

    query = "Is CS 3110 offered in the fall?"
    generate(query, FAKE_CHUNKS)

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args[1]["messages"]
    full_text = " ".join(m["content"] for m in messages)
    assert query in full_text


@patch("pipeline.generate.Groq")
def test_generate_empty_chunks_still_runs(mock_groq_cls):
    mock_groq_cls.return_value.chat.completions.create.return_value = make_mock_groq_response(
        "I don't have enough information to answer that."
    )
    result = generate("What is the meaning of life?", [])
    assert isinstance(result, str)


@patch("pipeline.generate.Groq")
def test_generate_api_error_returns_fallback(mock_groq_cls):
    mock_groq_cls.return_value.chat.completions.create.side_effect = Exception("API timeout")
    result = generate("Is CS 3110 offered in the fall?", FAKE_CHUNKS)
    assert isinstance(result, str)
    assert len(result) > 0


@patch("pipeline.generate.Groq")
def test_generate_uses_correct_model(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_response()
    mock_groq_cls.return_value = mock_client

    generate("test query", FAKE_CHUNKS)

    call_args = mock_client.chat.completions.create.call_args
    assert call_args[1]["model"] == "llama-3.3-70b-versatile"


@patch("pipeline.generate.Groq")
def test_generate_system_prompt_frames_cornell_advisor(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_response()
    mock_groq_cls.return_value = mock_client

    generate("test query", FAKE_CHUNKS)

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args[1]["messages"]
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    assert "Cornell" in system_msg or "advisor" in system_msg.lower()


# ── Integration tests (real Groq API) ────────────────────────────────────────

@pytest.mark.integration
def test_real_generate_returns_nonempty():
    result = generate("Is CS 3110 offered in the fall?", FAKE_CHUNKS)
    assert isinstance(result, str)
    assert len(result) > 10


@pytest.mark.integration
def test_real_generate_relevant_to_query():
    result = generate("Is CS 3110 offered in the fall?", FAKE_CHUNKS)
    # Answer should reference fall or FA semesters given the context chunks
    assert any(word in result.lower() for word in ["fall", "fa", "yes", "offered", "semester"])


@pytest.mark.integration
def test_real_generate_empty_chunks_graceful():
    result = generate("What is CS 3110?", [])
    assert isinstance(result, str)
    assert len(result) > 0
