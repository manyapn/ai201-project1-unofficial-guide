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

**Final chunk count:** 4,856 chunks across 3,316 documents (375 course docs from Cornell Classes API across 4 semesters, 1,255 docs from CUReviews including per-course schedule docs with professor-semester associations, 1,682 RateMyProfessors reviews for CS faculty, and 4 local requirement docs).

---

## Sample Chunks

Five representative chunks from different source types, showing what the embedding model actually stores:

**[1] affiliation_eng.txt (requirement doc)**
> CS Affiliation Requirements - College of Engineering (Bowers CIS)
> EN students must meet all of the following requirements to be eligible to apply to affiliate with the CS major:
> General Requirement
> A minimum grade of "C" (not C-) in all completed CS, MATH, and CS-designated Critical Math Courses at the time the affiliation application is reviewed, even if those courses are not required for affil

**[2] CUReviews (course review, CS 3110)**
> CS 3110 (Data Structures and Functional Programming) review: I'm not a big OCaml fan, but Clarkson makes learning it as painless as possible.

**[3] RateMyProfessors (professor review)**
> Review of Professor Robert Kleinberg for CS4820: He is extremely intelligent and very committed in helping his students learn the material. He can be a little brash when dealing with administrative issues in the course, but seems genuinely interested in his teaching duties. Would highly recommend taking 4820 under him if you want to seriously test your understanding of algorithms.

**[4] Cornell Classes API (course doc, FA26)**
> CS 3110: Functional Programming and Data Structures Advanced programming course emphasizing functional programming, data structures, and software design. Topics include recursive and higher-order programming, algebraic data types and pattern matching, modularity and abstraction mechanisms, models of program evaluation, and type systems. Covers techniques for specifying, testing, and reasoning abou

**[5] CUReviews (course_schedule doc)**
> CS 1340 (Choices and Consequences in Computing) semester history. Fall semesters offered: none recorded. Spring semesters offered: SP21, SP22, SP24, SP25. Professors by semester (inferred from student reviews): FA22: Jon Kleinberg, Karen Levy. FA24: Jon Kleinberg, Karen Levy. SP21: Jon Kleinberg, Karen Levy.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, runs locally with no API key.

**Production tradeoff reflection:** `all-MiniLM-L6-v2` is fast and free but has a 256-token context window that can truncate longer requirement paragraphs. For a real deployment, `text-embedding-3-small` (OpenAI) would give better semantic accuracy and a larger context window at the cost of API latency and per-token pricing. For tighter accuracy on Cornell-specific terms like "prelim," "curve," "p/f," or "affiliate," fine-tuning on Cornell review text could help, though it's probably overkill at this scale.

---

## Retrieval Test Results

**Query 1: "What grades do I need to affiliate with CS as an Engineering student?"**

| Rank | Similarity | Source | Preview |
|------|-----------|--------|---------|
| 1 | 0.39 | affiliation_eng.txt (requirement) | CS Affiliation Requirements - College of Engineering... A minimum grade of "C" (not C-) in all completed CS, MATH, and CS-designated Critical Math Courses... |
| 2 | 0.27 | affiliation_as.txt (requirement) | CS Affiliation Requirements - College of Arts and Sciences... A&S students must meet all of the following requirements... |
| 3 | 0.23 | cs_bs_requirements.txt (requirement) | ...One 3+ credit course or combination equaling 3+ credits. NOT allowed: PE courses, courses numbered 10xx or below... |
| 4 | 0.16 | affiliation_eng.txt (requirement) | ...Computer Science Requirements: These courses must be completed with a minimum grade of "C" (not "C-") in each... |

**Why these chunks are relevant:** All four are from requirement documents and directly address affiliation grade rules. The top chunk has the highest similarity (0.39) and opens with the exact phrase being asked about. Chunks 2-4 fill in the specific course requirements (CS 2110, CS 2800, MATH 1920). The retrieval correctly prioritized requirement docs over course reviews because the query contains "affiliate" and "Engineering student," which are requirement-query keywords that route retrieval to `doc_type: requirement` filtered search.

---

**Query 2: "What do students say about CS 3110 with Clarkson?"**

| Rank | Similarity | Source | Preview |
|------|-----------|--------|---------|
| 1 | 0.51 | RateMyProfessors (review, Michael Clarkson) | Review of Professor Michael Clarkson for CS3110: I dont understand the hype around clarkson. He is not a great lecturer... |
| 2 | 0.49 | RateMyProfessors (review, Michael Clarkson) | Review of Professor Michael Clarkson for CS3110: Simply not the best. |
| 3 | 0.48 | RateMyProfessors (review, Michael Clarkson) | Review of Professor Michael Clarkson for CS3110: Clarkson is a phenomenal CS lecturer who deeply cares about his students... |
| 4 | 0.48 | RateMyProfessors (review, Michael Clarkson) | Review of Professor Michael Clarkson for CS3110: nn |

**Why these chunks are relevant:** All four are RMP reviews explicitly naming both Clarkson and CS3110. Similarities are high (0.48-0.51) because the query text matches the review text closely. The retrieval correctly uses `course_number: "CS 3110"` filtering combined with the professor name in the query to surface only Clarkson-specific reviews rather than all CS 3110 reviews. The reviews show genuine disagreement about Clarkson, which allows the model to present a balanced answer.

---

**Query 3: "Is CS 4820 required for the CS BA?"**

| Rank | Similarity | Source | Preview |
|------|-----------|--------|---------|
| 1 | 0.19 | cs_ba_requirements.txt (requirement) | CS BA Degree Requirements - College of Arts and Sciences, 2025-2026 Edition... |
| 2 | 0.04 | cs_bs_requirements.txt (requirement) | ...CS 5625 - Interactive Computer Graphics, CS 5643 - Physically Based Animation... |
| 3 | 0.03 | cs_ba_requirements.txt (requirement) | ...Technical Electives: Complete three 3000+ level technical electives... |
| 4 | 0.02 | cs_bs_requirements.txt (requirement) | CS BS Degree Requirements - College of Engineering (Bowers CIS), 2025-2026 Edition... |

These similarities are low (0.02-0.19) because the query doesn't share words with course descriptions. The system uses a `where_document={"$contains": "CS 4820"}` keyword filter pass specifically for this case, guaranteeing chunks that literally mention CS 4820 are surfaced regardless of semantic ranking. This hybrid approach (semantic + keyword) is what makes the answer accurate after the initial failure case was analyzed and fixed.

---

## Grounded Generation

**System prompt grounding instruction:** The system prompt tells the model: "You are a knowledgeable Cornell University CS advisor. Answer the student's question using only the context provided below. If the context does not contain enough information, say so honestly. Be concise and specific. Do not invent facts." Retrieved chunks are numbered and passed as a context block before the user's question. The model is instructed not to go beyond what's in those chunks.

**How source attribution is surfaced in the response:** The Gradio UI has an expandable Sources section below every answer. Each source shows the chunk's origin (Cornell Classes API, CUReviews, RateMyProfessors, or a local doc), similarity score, and a 200-character text preview so the user can verify what the model used. The system prompt also instructs the model to end every answer with a "Sources:" line listing the source labels it drew from, so attribution appears in the answer text itself, not just the accordion.

---

## Example Responses

**Example 1: "What do students say about the workload in CS 3110?"**

> Students have varying opinions about the workload in CS 3110. Some students, such as those in SP22 with Nate Foster and Justin Hsu (Source: CUReviews), and SP25 with Anshuman Mohan (Source: CUReviews), found the workload to be manageable, with assignments taking around 8-16 hours per two weeks. However, others, such as a student with Nate Foster (Source: RateMyProfessors), and students in SP21 with Michael Clarkson (Source: CUReviews), and SP25 with Anshuman Mohan (Source: CUReviews), found the workload to be relatively high or overwhelming, with some assignments being stressful and time-consuming.
>
> Sources: RateMyProfessors, CUReviews

Source attribution is explicit in the answer body (citing professor and semester per claim) and in the Sources line. The response draws from both CUReviews and RateMyProfessors and attributes each claim to its specific semester and professor.

---

**Example 2: "Is CS 4820 required for both the BA and BS?"**

> Yes, CS 4820 - Introduction to Analysis of Algorithms is required for both the BA and BS degrees in Computer Science, as it is listed as a requirement in both cs_ba_requirements.txt and cs_bs_requirements.txt.
>
> Sources: cs_ba_requirements.txt, cs_bs_requirements.txt

The answer cites the exact document filenames as sources. This is directly grounded in the retrieved requirement doc chunks and does not rely on the model's general knowledge about Cornell.

---

**Out-of-scope query: "What is the best dining hall at Cornell?"**

> The context provided does not contain enough information to answer the question about the best dining hall at Cornell. The context only discusses course experiences with various professors and does not mention dining halls.
>
> Sources: RateMyProfessors, CUReviews

The system correctly refuses to answer. The retrieved chunks are CS course reviews (the only documents in the system), so the model has no relevant context and says so rather than hallucinating a dining recommendation.

---

## Query Interface

**Input field:** A text box labeled "Your question" with placeholder text showing example queries. Accepts free-text questions. Submits on Enter or by clicking the "Ask" button.

**Output fields:**
- "Answer" text box (read-only, 6 lines): the model-generated response grounded in retrieved chunks. Always ends with a "Sources:" line listing which data sources were used.
- "Sources used" accordion (collapsed by default): expands to show each retrieved chunk with its label (source type, course number or professor), similarity score, and a 200-character text preview. Clicking the accordion lets the user verify exactly what the model saw.

**Sample interaction transcript:**

```
Input: What counts as a practicum or project course for the CS major?

Answer:
According to cs_ba_requirements.txt and cs_bs_requirements.txt, the following courses
count as practicum/project courses for the CS major:
  - CS 3152 - Introduction to Computer Game Development
  - CS 4121 - Practicum in Information Science
  - CS 4152 - Advanced Topics in Computer Game Development
  - CS 4321 - Practicum in Databases and Information Systems
  - CS 4411 - Practicum in Operating Systems
  - CS 4621 - Computer Graphics Practicum

Note: CS 4090, CS 4997, CS 4998, and CS 4999 are explicitly listed as NOT allowed
to count for this requirement.

Sources: cs_ba_requirements.txt, cs_bs_requirements.txt

Sources used (expanded):
[1] Requirement doc: cs_ba_requirements.txt (similarity: 0.46)
> ...Complete one of the following practicum/project courses: CS 3152 - Introduction to
  Computer Game Development CS 4121 - Practicum in Informati...
[2] Requirement doc: cs_bs_requirements.txt (similarity: 0.38)
> ...CS 4090, CS 4997, CS 4998, CS 4999 not allowed for practicum requirement...
```

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What grades do I need to affiliate with CS as an Engineering student? | C (not C-) in CS 2110 and CS 2800, average at least 2.50, C or higher in MATH 1920, critical math average at least 2.30 | "Minimum grade of C (not C-) in all completed CS, MATH, and CS-designated Critical Math Courses at the time the affiliation application is reviewed" | Relevant | Partially accurate (correct on grade floor, missed the specific 2.50 average and MATH 1920 detail) |
| 2 | What do students say about the workload in CS 3110? | Heavy problem sets, challenging final project, steep OCaml learning curve | Cites per professor+semester: "relatively high (SP21 with Clarkson), manageable (SP22 with Foster), weekly projects time-consuming (SP25 with Mohan)" | Relevant | Accurate |
| 3 | Is CS 4820 required for both the BA and BS? | Yes, CS 4820 is a core requirement for both tracks | "Yes, required for both BA and BS" with sources citing cs_ba_requirements.txt and cs_bs_requirements.txt | Relevant | Accurate |
| 4 | What are students' biggest complaints about CS 4820? | Fast-paced lectures, hard problem sets, assumes strong math background | "Disorganized class, delayed and inconsistent grading, large time commitment (up to 10 hrs/week), content is just plain hard" | Relevant | Accurate |
| 5 | What counts as a practicum or project course for the CS major? | CS 4121, CS 4321, CS 4411, CS 4621, CS 4701, CS 3152, CS 4152; one required for both BA and BS | "CS 3152, CS 4121, CS 4152, CS 4321, CS 4411, CS 4621; select one; CS 4090/4997/4998/4999 not allowed" | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed (initial version):** "Is CS 4820 required for both the BA and BS?"

**What the system returned:** The model confirmed CS 4820 is required for the BS but couldn't confirm the BA. It correctly retrieved a BS requirement chunk listing CS 4820 explicitly, but the BA requirement chunk was the document header (first 400 characters of cs_ba_requirements.txt) - just the degree name and credit total, not the core course list.

**Root cause (tied to a specific pipeline stage):** Chunking and retrieval together. The BA requirement document is chunked in 400-character windows starting from the top. The first chunk is the header. The chunk listing CS 4820 as required is several windows deep. Semantic similarity between "Is CS 4820 required for the BA?" and the header chunk was high enough to surface it over the specific chunk that names 4820.

**Fix applied:** Added a `where_document={"$contains": "CS 4820"}` keyword filter pass on requirement docs in `smart_retrieve()`. This guarantees that chunks literally containing "CS 4820" are retrieved regardless of semantic ranking. The system now correctly confirms both BA and BS.

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
