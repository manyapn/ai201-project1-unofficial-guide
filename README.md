# The Unofficial Cornell CS Guide

---

## Domain

Cornell CS degree planning for students in the A&S (BA) and Engineering (BS) tracks. The course catalog, Bowers affiliation page, and classes.cornell.edu are spread across five or more different sites, all written in bureaucratic language that makes it hard to answer questions like "what do I need to affiliate?" or "is CS 3110 worth taking?" CUReviews and RateMyProfessors fill in the student perspective but require separate searches. This system pulls all of it together so you can plan your CS degree without switching tabs.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | CUReviews | Student course reviews (text + ratings) | https://www.cureviews.org/ |
| 2 | RateMyProfessors | Professor ratings and review text | https://www.ratemyprofessors.com/ (GraphQL API, school ID 298) |
| 3 | Cornell Classes API (FA26) | Official course roster: title, description, prerequisites, instructors | https://classes.cornell.edu/api/2.0/search/classes.json?roster=FA26&subject=CS |
| 4 | Cornell Classes API (SP26) | Official course roster | https://classes.cornell.edu/api/2.0/search/classes.json?roster=SP26&subject=CS |
| 5 | Cornell Classes API (FA25) | Official course roster | https://classes.cornell.edu/api/2.0/search/classes.json?roster=FA25&subject=CS |
| 6 | Cornell Classes API (SP25) | Official course roster | https://classes.cornell.edu/api/2.0/search/classes.json?roster=SP25&subject=CS |
| 7 | CS BA degree requirements | Full A&S BA program requirements | documents/cs_ba_requirements.txt |
| 8 | CS BS degree requirements | Full Engineering BS program requirements | documents/cs_bs_requirements.txt |
| 9 | CS affiliation requirements (A&S) | Grade and GPA requirements to declare the CS major | documents/affiliation_as.txt |
| 10 | CS affiliation requirements (Engineering) | Grade and GPA requirements to affiliate with CS | documents/affiliation_eng.txt |

---

## Chunking Strategy

**Chunk size:** 400 characters

**Overlap:** 50 characters

**Why these choices fit your documents:** CUReviews and RMP reviews are short, typically under 400 characters, so most fit in a single chunk. Longer texts like requirement paragraphs or course descriptions may split at a character boundary, but the 50-character overlap means the next chunk re-enters with enough context to still make sense. The requirement docs are chunked small on purpose: retrieval should return the specific rule being asked about, not the whole page. Each chunk stores a `chunk_index` field so the generation step can tell which part of a source doc it came from.

**Final chunk count:** 4,570 chunks across 3,100 documents (375 course docs from Cornell Classes API across 4 semesters, 1,255 docs from CUReviews including per-course schedule docs with professor-semester associations, 1,466 RateMyProfessors reviews for CS faculty, and 4 local requirement docs).

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, runs locally with no API key.

**Production tradeoff reflection:** `all-MiniLM-L6-v2` is fast and free but has a 256-token context window that can truncate longer requirement paragraphs. For a real deployment, `text-embedding-3-small` (OpenAI) would give better semantic accuracy and a larger context window at the cost of API latency and per-token pricing. For tighter accuracy on Cornell-specific terms like "prelim," "curve," "p/f," or "affiliate," fine-tuning on Cornell review text could help, though it's probably overkill at this scale.

---

## Grounded Generation

**System prompt grounding instruction:** The system prompt tells the model: "You are a knowledgeable Cornell University CS advisor. Answer the student's question using only the context provided below. If the context does not contain enough information, say so honestly. Be concise and specific. Do not invent facts." Retrieved chunks are numbered and passed as a context block before the user's question. The model is instructed not to go beyond what's in those chunks.

**How source attribution is surfaced in the response:** The Gradio UI has an expandable Sources section below every answer. Each source shows the chunk's origin (Cornell Classes API, CUReviews, RateMyProfessors, or a local doc), similarity score, and a 200-character text preview so the user can verify what the model used.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What grades do I need to affiliate with CS as an Engineering student? | C (not C-) in CS 2110 and CS 2800, average at least 2.50, C or higher in MATH 1920, critical math average at least 2.30 | "Minimum grade of C (not C-) in all completed CS, MATH, and CS-designated Critical Math Courses" | Relevant | Partially accurate (correct on grade floor, missed the specific 2.50 average requirement) |
| 2 | What do students say about the workload in CS 3110? | Heavy problem sets, challenging final project, steep OCaml learning curve | "Not enough information — context only mentions 3110 in comparison to other courses" | Off-target | Inaccurate |
| 3 | Is CS 4820 required for both the BA and BS? | Yes, CS 4820 is a core requirement for both tracks | "Context does not contain enough information" | Partially relevant | Inaccurate |
| 4 | What are students' biggest complaints about CS 4820? | Fast-paced lectures, hard problem sets, assumes strong math background | "No complaints — the only retrieved review said nothing to complain about" | Off-target | Inaccurate |
| 5 | What counts as a practicum or project course for the CS major? | CS 4740, CS 5150, CS 4321, CS 3152, CS 4411, and others; one required for both tracks | "Context only mentions CS 4997 as independent study, not a practicum list" | Off-target | Inaccurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** "What do students say about the workload in CS 3110?"

**What the system returned:** The model said there was not enough information. The retrieved chunks were CUReviews reviews, but they mentioned CS 3110 only as a comparison point in reviews for other courses ("CS 4410 was less time-consuming than CS 3110"), not as the primary subject.

**Root cause (tied to a specific pipeline stage):** Retrieval stage. The query "workload in CS 3110" embedded into a vector that matched reviews where 3110 appeared as a side mention rather than the main topic. CUReviews reviews are stored as full review text without a strong course-number anchor in the embedding, so semantic similarity pulled in reviews that were loosely related rather than directly about CS 3110. The 3110-specific reviews exist in the database but ranked lower than cross-course comparisons.

**What you would change to fix it:** Prepend the course number to the chunk text more aggressively (e.g., "CS 3110 student review: [text]") so the embedding carries a stronger course-number signal. Alternatively, add a metadata pre-filter on `course_number == "CS 3110"` before the semantic search to narrow the candidate pool before ranking.

---

## Spec Reflection

**One way the spec helped during implementation:** The metadata schema I defined in planning.md (source, doc_type, course_number, semester, is_current, professor_name) paid off during the embedding step. When I hit the ChromaDB None-rejection bug, having a typed schema meant I knew exactly which fields could be None and could write `sanitize_metadata()` targeting those fields. Without the schema defined upfront, I would have discovered the bug field-by-field at runtime.

**One way the implementation diverged from the spec:** planning.md described CUReviews as an HTML scraping target. When I actually looked at the site, it's a React SPA with no server-rendered HTML. The data comes from a JSON API. The spec had to be updated to reflect that scraping approach, and the ingest code uses POST requests to `/api/courses/get-by-info` and `/api/courses/get-reviews` instead of BeautifulSoup.

---

## AI Usage

**Instance 1**

- *What I gave the AI:* My chunking strategy from planning.md (chunk size 400, overlap 50, reasoning about review length) and the metadata schema I wanted attached to each chunk.
- *What it produced:* `chunk_text(text, chunk_size=400, overlap=50, metadata=None)` using a character-based sliding window.
- *What I changed or overrode:* Added `chunk_index` to the metadata after the grader flagged that without a positional index, retrieved chunks from long documents couldn't be attributed to a specific part of the source. The original implementation didn't include it.

**Instance 2**

- *What I gave the AI:* The RateMyProfessors GraphQL endpoint, the school ID (298), and the problem that only 25 CS professors were returned when the site showed 99.
- *What it produced:* A paginated fetch loop using `pageInfo { hasNextPage endCursor }` and an `after:` cursor argument to walk through all result pages.
- *What I changed or overrode:* Added client-side filtering on `department == "Computer Science"` after discovering the GraphQL `departmentID` parameter returns 0 results (it's a frontend-only URL parameter, not a real API filter). The AI's first version passed `departmentID` to the query and got nothing back.
