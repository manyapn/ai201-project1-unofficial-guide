# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

Cornell CS degree planning for students in both the A&S (BA) and Engineering (BS) tracks.

The course catalog, Bowers affiliation page, and classes.cornell.edu are spread across five or more different sites, all written in bureaucratic language that makes it hard to answer simple questions like "what do I need to affiliate?" or "is CS 3110 worth taking?" CUReviews and RateMyProfessors fill in the student side but require separate searches. This system pulls it all together so you can plan your CS degree without switching tabs.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | CUReviews | Student-written reviews (text + ratings) for Cornell CS courses | https://www.cureviews.org/ |
| 2 | RateMyProfessors | Professor ratings, difficulty scores, and review text for Cornell CS faculty | https://www.ratemyprofessors.com/ (GraphQL API, school ID 298) |
| 3 | Cornell Classes API (FA26) | Official FA26 CS course roster: title, description, credits, prerequisites, instructors | https://classes.cornell.edu/api/2.0/search/classes.json?roster=FA26&subject=CS |
| 4 | Cornell Classes API (SP26) | Official SP26 CS course roster | https://classes.cornell.edu/api/2.0/search/classes.json?roster=SP26&subject=CS |
| 5 | Cornell Classes API (FA25) | Official FA25 CS course roster | https://classes.cornell.edu/api/2.0/search/classes.json?roster=FA25&subject=CS |
| 6 | Cornell Classes API (SP25) | Official SP25 CS course roster | https://classes.cornell.edu/api/2.0/search/classes.json?roster=SP25&subject=CS |
| 7 | CS BA degree requirements (A&S) | Full BA program requirements including math, core, electives, and external specialization | documents/cs_ba_requirements.txt |
| 8 | CS BS degree requirements (Engineering) | Full BS program requirements including engineering core and technical electives | documents/cs_bs_requirements.txt |
| 9 | CS affiliation requirements (A&S) | Grade and GPA requirements to declare the CS major as an A&S student | documents/affiliation_as.txt |
| 10 | CS affiliation requirements (Engineering) | Grade and GPA requirements to affiliate with the CS major as an Engineering student | documents/affiliation_eng.txt |

---

## Chunking Strategy

**Chunk size:** 400 characters

**Overlap:** 50 characters

**Reasoning:**
CUReviews and RMP reviews are short by nature, typically 1-4 sentences and under 400 characters, so most fit in a single chunk without splitting. Longer texts like requirement paragraphs or course descriptions may split at a character boundary, but the 50-character overlap means the next chunk re-enters with enough context to still make sense. The requirement docs are chunked small on purpose: retrieval should return the specific rule someone is asking about (like the "C not C-" policy or the 2.50 average requirement), not the whole page. Each chunk also stores a `chunk_index` so the generation step can tell which part of a source doc it came from.

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` (runs locally, no API key needed)

**Top-k:** 5

**Production tradeoff reflection:**
`all-MiniLM-L6-v2` is fast and free but has a 256-token context window that can truncate longer requirement paragraphs. For a production system, `text-embedding-3-small` (OpenAI) would give better semantic accuracy and a larger context window, at the cost of API latency and per-token pricing. For tighter accuracy on Cornell-specific terms ("prelim," "curve," "p/f," "affiliate"), fine-tuning on Cornell review text could help, though it's probably overkill at this scale.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What grades do I need to affiliate with the CS major as an Engineering student? | C (not C-) in CS 2110 and CS 2800 with an average of at least 2.50; C or higher in MATH 1920; overall critical math average of at least 2.30 |
| 2 | What do students say about the workload in CS 3110? | Reviews mention heavy weekly problem sets, a challenging final project, and a steep learning curve for functional programming |
| 3 | Is CS 4820 required for both the BA and BS? | Yes. CS 4820 (Algorithms) is a core requirement for both the A&S BA and the Engineering BS |
| 4 | What are students' biggest complaints about CS 4820? | Reviews cite fast-paced lectures, difficult problem sets, and that strong mathematical maturity is assumed |
| 5 | What counts as a practicum or project course for the CS major? | Lists courses like CS 4740, CS 5150, CS 4321, CS 3152, CS 4411, and others; one is required for both BA and BS |

---

## Anticipated Challenges

1. **Short reviews embed poorly**: Many CUReviews and RMP reviews are one sentence ("Great professor, hard exams"). Very short chunks may not carry enough semantic signal to retrieve reliably for specific queries, causing the system to return loosely related results instead of the most relevant review.

2. **Degree requirement text is structured, not conversational**: The affiliation and degree requirement documents use formal, list-heavy language that embeds differently than review prose. A query phrased naturally ("what do I need to declare CS?") may not match the formal phrasing in the document ("minimum grade of C (not C-) in all completed CS, MATH, and CS-designated Critical Math Courses"). Retrieval may miss the right chunk if the semantic gap between the query and the document language is too large.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Document Ingestion                        │
│                                                              │
│  Cornell Classes API  →  JSON dicts (course metadata)        │
│  CUReviews scraper    →  HTML → parsed review dicts          │
│  RateMyProfessors GQL →  JSON (professor ratings + reviews)  │
│  Local .txt files     →  degree + affiliation requirements   │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                         Chunking                              │
│                                                              │
│  chunk_text(): 400-char chunks, 50-char overlap              │
│  Each chunk tagged with metadata:                            │
│    source, course_number, professor_name, semester, doc_type │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│               Embedding + Vector Store                        │
│                                                              │
│  Model: all-MiniLM-L6-v2 (sentence-transformers, local)      │
│  Store: ChromaDB (local persistent collection)               │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                         Retrieval                             │
│                                                              │
│  User query → embed → cosine similarity search               │
│  Return top-5 chunks with metadata                           │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                         Generation                            │
│                                                              │
│  Groq API: llama-3.3-70b-versatile                           │
│  System prompt: answer only from retrieved context,          │
│    cite source + course number for every claim               │
│  Interface: Gradio                                           │
└──────────────────────────────────────────────────────────────┘
```

---

## AI Tool Plan

**Milestone 3: Ingestion and chunking**
Used Claude to implement `chunk_text(text, chunk_size=400, overlap=50)`. Gave it my chunking strategy as input and had it produce a function that splits text with overlap. Verified by running it on a sample CUReviews review and a paragraph from the affiliation requirements, checking that chunk sizes were right and metadata fields (source, course_number, doc_type, chunk_index) attached correctly.

**Milestone 4: Embedding and retrieval**
Used Claude to implement `embed_and_store(chunks)` and `retrieve(query, k=5)`. Gave it the stack (sentence-transformers, ChromaDB) and the metadata schema. Verified by querying the 5 evaluation questions directly against the vector store and checking that returned chunks were topically relevant. A question about affiliation requirements should come back with requirement chunks, not course reviews.

**Milestone 5: Generation and interface**
Used Claude to draft the system prompt for the Groq generation step. Gave it the grounding requirement (answer only from context, cite source by name and course number) and had it produce the prompt string. Evaluated by running all 5 test questions end-to-end and checking whether the model cites sources correctly and stays within the retrieved context.
