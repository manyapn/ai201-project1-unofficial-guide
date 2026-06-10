import gradio as gr
from pipeline.embed import smart_retrieve
from pipeline.generate import generate

CHROMA_PATH = "chroma_db"


def answer(query):
    if not query or not query.strip():
        return "Please enter a question.", ""

    chunks = smart_retrieve(query, k=7, chroma_path=CHROMA_PATH)
    if not chunks:
        return "No relevant information found in the database. Try running build_db.py first.", ""

    response = generate(query, chunks)

    sources_lines = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        doc_type = meta.get("doc_type", "unknown")
        source = meta.get("source", "unknown")

        if doc_type == "course":
            label = f"Cornell Classes API : {meta.get('course_number', '')} ({meta.get('semester', '')})"
        elif doc_type == "course_schedule":
            label = f"CUReviews schedule : {meta.get('course_number', '')}"
        elif doc_type == "review" and source == "cureviews":
            prof = meta.get("professor", "unknown professor")
            label = f"CUReviews review : {meta.get('course_number', '')} ({prof})"
        elif doc_type == "review" and source == "ratemyprofessors":
            label = f"RateMyProfessors : {meta.get('professor_name', '')}"
        elif doc_type == "requirement":
            label = f"Requirement doc : {meta.get('source', '')}"
        else:
            label = f"{source} / {doc_type}"

        preview = chunk["text"][:200].replace("\n", " ")
        dist = chunk.get("distance", 0)
        sources_lines.append(f"**[{i}] {label}** (similarity: {1 - dist:.2f})\n> {preview}...")

    sources_text = "\n\n".join(sources_lines)
    return response, sources_text


with gr.Blocks(title="The Unofficial Cornell CS Guide") as demo:
    gr.Markdown("# The Unofficial Cornell CS Guide")
    gr.Markdown(
        "Ask anything about Cornell CS courses, professors, degree requirements, or affiliation rules. "
        "Answers are generated from student reviews, official course data, and degree requirement documents."
    )

    with gr.Row():
        with gr.Column(scale=2):
            query_box = gr.Textbox(
                label="Your question",
                placeholder="e.g. Is CS 3110 offered in the fall? What do students say about CS 4820?",
                lines=2
            )
            submit_btn = gr.Button("Ask", variant="primary")

    answer_box = gr.Textbox(label="Answer", lines=6, interactive=False)

    with gr.Accordion("Sources used", open=False):
        sources_box = gr.Markdown()

    submit_btn.click(fn=answer, inputs=query_box, outputs=[answer_box, sources_box])
    query_box.submit(fn=answer, inputs=query_box, outputs=[answer_box, sources_box])

if __name__ == "__main__":
    demo.launch()
