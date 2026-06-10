import os
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a knowledgeable Cornell University CS advisor. "
    "Answer the student's question using only the context provided below. "
    "If the context does not contain enough information, say so honestly. "
    "Be concise and specific. Do not invent facts. "
    "When discussing course experiences from student reviews, always cite the "
    "professor and semester for each claim (e.g. 'FA23 with Nate Foster: ...'). "
    "Different professors and semesters can have very different experiences, "
    "so always attribute claims to their source. "
    "When comparing two or more courses, address each one separately and "
    "proportionally to the evidence available. Do not bias toward whichever "
    "course appears first in the context. If the context has much more "
    "information about one course than another, say so explicitly rather than "
    "implying they are equally well-documented. "
    "When a course number is 5000-level or above, note that it is a graduate-level "
    "course and that undergraduates typically need permission to enroll. "
    "At the end of your answer, include a 'Sources:' line listing the source "
    "labels (e.g. CUReviews, RateMyProfessors, Cornell Classes API, "
    "cs_ba_requirements.txt) for the chunks you drew from."
)


def _infer_semester(date_str):
    if not date_str:
        return None
    try:
        clean = date_str.replace("T", " ").split(".")[0].strip()
        dt = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
        suffix = str(dt.year)[2:]
        return f"FA{suffix}" if dt.month > 5 else f"SP{suffix}"
    except Exception:
        return None


def _format_chunk(i, chunk):
    text = chunk["text"]
    meta = chunk.get("metadata", {})
    doc_type = meta.get("doc_type", "")
    source = meta.get("source", "")

    source_label = {
        "cureviews": "CUReviews",
        "ratemyprofessors": "RateMyProfessors",
        "cornell_classes_api": "Cornell Classes API",
    }.get(source, source)

    parts = [f"Source: {source_label}"] if source_label else []

    if doc_type == "review":
        prof = meta.get("professor") or meta.get("professor_name") or ""
        sem = _infer_semester(meta.get("date", ""))
        if sem:
            parts.append(sem)
        if prof:
            parts.append(f"Prof: {prof}")

    elif doc_type == "course":
        sem = meta.get("semester", "")
        instructors = meta.get("instructors", "")
        if sem:
            parts.append(sem)
        if instructors:
            parts.append(f"Instructors: {instructors}")

    label = f"({', '.join(parts)}) " if parts else ""
    return f"[{i+1}] {label}{text}"


def generate(query, chunks):
    context_block = "\n\n".join(
        _format_chunk(i, c) for i, c in enumerate(chunks)
    ) if chunks else "No context available."

    user_message = f"Context:\n{context_block}\n\nQuestion: {query}"

    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Sorry, I was unable to generate a response. ({e})"
