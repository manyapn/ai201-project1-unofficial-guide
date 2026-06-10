import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a knowledgeable Cornell University CS advisor. "
    "Answer the student's question using only the context provided below. "
    "If the context does not contain enough information, say so honestly. "
    "Be concise and specific. Do not invent facts."
)


def generate(query, chunks):
    context_block = "\n\n".join(
        f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)
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
