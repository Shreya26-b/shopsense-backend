# services/rag.py
from services.faiss_index import search_index
from dotenv import load_dotenv
import os

load_dotenv()

HF_API_TOKEN = os.getenv("HF_API_TOKEN")


# ── Prompt Template ───────────────────────────────────────

def build_prompt(
    question: str,
    chunks: list[str],
    conversation_history: list[dict] = []
) -> str:
    """
    Assembles the complete prompt from:
    - System instructions (how the AI should behave)
    - Retrieved data chunks (the context)
    - Conversation history (for follow-up questions)
    - The current question

    The prompt structure directly determines answer quality.
    """

    # Format retrieved chunks as numbered list
    context = "\n".join([
        f"[{i+1}] {chunk}"
        for i, chunk in enumerate(chunks)
    ])

    # Format conversation history for multi-turn chat
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation:\n"
        for msg in conversation_history[-4:]:  # last 4 exchanges only
            role   = "User"      if msg["role"] == "user"      else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    # The complete prompt
    prompt = f"""You are a helpful analytics assistant for an e-commerce store owner.
Your job is to answer questions about their store performance using the provided data.

Important rules:
- Use ONLY the data provided below to answer
- Never make up numbers, dates, or facts not in the data
- Be specific and mention actual product names, amounts, and dates
- If the data doesn't contain enough information, say so clearly
- Keep answers concise and actionable

Store data:
{context}
{history_text}
Current question: {question}

Answer:"""

    return prompt


# ── RAG Pipeline ──────────────────────────────────────────

async def run_rag_query(
    user_id: str,
    question: str,
    conversation_history: list[dict] = []
) -> dict:
    """
    The complete RAG pipeline:
    1. Retrieve relevant chunks from FAISS
    2. Build the prompt
    3. Call the LLM (added in Step 15)
    4. Return the answer

    Returns a dict with the answer and metadata.
    """

    # ── Step 1: Retrieve relevant chunks ─────────────────
    print(f"🔍 Searching index for: '{question[:50]}...'")
    results = search_index(user_id, question, top_k=5)

    if not results:
        return {
            "answer":  "I couldn't find any relevant data. Please build your index first using POST /index/build.",
            "chunks":  [],
            "sources": 0
        }

    # Extract just the text from results
    chunks = [r["chunk"] for r in results]
    print(f"📚 Retrieved {len(chunks)} relevant chunks")

    # ── Step 2: Build the prompt ──────────────────────────
    prompt = build_prompt(question, chunks, conversation_history)
    print(f"📝 Prompt assembled ({len(prompt)} characters)")

    # ── Step 3: Call the LLM ──────────────────────────────
    # Placeholder for now — replaced in Step 15
    # For testing, return the prompt so you can see what
    # gets sent to the LLM
    answer = await call_llm(prompt)

    return {
        "answer":  answer,
        "chunks":  chunks,        # which data was used
        "sources": len(chunks)    # how many chunks retrieved
    }


# ── LLM Call ─────────────────────────────────────────────

async def call_llm(prompt: str) -> str:
    """
    Calls the Hugging Face Inference API with the prompt.
    Replaced with full implementation in Step 15.
    For now returns a placeholder so we can test the pipeline.
    """
    return f"[LLM not connected yet — Step 15]\n\nPrompt sent:\n{prompt[:300]}..."